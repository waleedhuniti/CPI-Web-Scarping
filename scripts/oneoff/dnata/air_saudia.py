"""saudia.com, return search, 1 adult economy: per leg, each non-stop SV flight's cheapest economy fare
(the airline's own availability JSON, dapi.saudia.com/airsearch/search/air-bounds).
lowest = cheapest flight, highest = dearest flight. Inbound prices come after selecting the cheapest
outbound fare, as a user would. If a leg has no non-stop flight on its day, the next day is searched (noted).
usage: xvfb-run -a python3 air_saudia.py OUT_YYYY-MM-DD BACK_YYYY-MM-DD res.json [AP=RUH]"""
import asyncio, json, re, sys, os, datetime as dt
from playwright.async_api import async_playwright  # plain Playwright: no stealth fork (CLAUDE.md)
EXE = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
OUT_D, BACK_D, RES = sys.argv[1:4]; AP = sys.argv[4] if len(sys.argv) > 4 else "RUH"
CITY = {"RUH": "Riyadh"}
def label(d):
    n = d.day; suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f'{d.strftime("%A")}, {n}{suf} {d.strftime("%B %Y")}'
def nonstop(resp, frm, to):
    fl = []
    for g in resp["data"]["airBoundGroups"]:
        segs = g["boundDetails"]["segments"]
        if len(segs) != 1: continue
        fid = segs[0]["flightId"]                         # SEG-SV585-DXBRUH-2026-11-01-0225
        if f"-{frm}{to}-" not in fid: continue
        eco = [a["prices"]["totalPrices"][0]["total"] for a in g["airBounds"]
               if all(x["cabin"] == "eco" for x in a["availabilityDetails"])]
        if eco: fl.append({"flight": fid.split("-")[1], "dep": fid[-4:-2] + ":" + fid[-2:], "from": float(min(eco))})
    return fl
async def click_dialogs(pg):
    for loc in (pg.get_by_text(re.compile(r"Don.t change")), pg.locator('mat-dialog-container button:has-text("Continue")')):
        try:
            if await loc.count() and await loc.first.is_visible(): await loc.first.click(timeout=3000)
        except Exception: pass
async def search(pg, out, back):
    bounds = []
    async def on(r):
        if "/airsearch/search/air-bounds" in r.url:
            try: bounds.append(json.loads(await r.text()))
            except Exception: pass
    pg.on("response", on)
    await pg.goto("https://www.saudia.com/en-AE", wait_until="domcontentloaded", timeout=60000)
    await pg.wait_for_timeout(8000)
    try: await pg.get_by_text("Yes, I accept").click(timeout=3000)
    except Exception: pass
    fr = pg.locator("input[placeholder=From]"); await fr.click(); await fr.fill(""); await pg.keyboard.type("Dubai", delay=110)
    await pg.wait_for_timeout(2000); await pg.locator('mat-option:has-text("DXB")').first.click(); await pg.wait_for_timeout(1200)
    await pg.locator("input[placeholder=To]").click(); await pg.keyboard.type(CITY[AP], delay=110)
    await pg.wait_for_timeout(2000); await pg.locator(f'mat-option:has-text("{AP}")').first.click(); await pg.wait_for_timeout(2500)
    if not await pg.locator("td.flightprice:visible").count():
        await pg.get_by_text("Departing", exact=True).first.click(); await pg.wait_for_timeout(1500)
    for d in (out, back):
        for _ in range(3):                                   # move the calendar forward if the month is not shown
            if await pg.locator(f'td[aria-label^="{label(d)}"]:visible').count(): break
            await pg.locator('button:has-text("arrow_forward"):visible, .mat-calendar-next-button:visible').last.click(); await pg.wait_for_timeout(800)
        await pg.locator(f'td[aria-label^="{label(d)}"]:visible').first.click(); await pg.wait_for_timeout(1200)
    await pg.locator('button[aria-label="Search Flights"]').evaluate("e=>e.click()")
    for _ in range(12):
        await pg.wait_for_timeout(2500); await click_dialogs(pg)
        if bounds: break
    await pg.wait_for_timeout(4000)
    if not bounds: raise RuntimeError("no outbound availability")
    # choose the cheapest outbound fare (first card is sorted lowest), so the inbound list is priced
    await pg.locator(".fare-details").first.evaluate("e=>e.scrollIntoView({block:'center'})"); await pg.wait_for_timeout(800)
    bb = await pg.locator(".fare-details").first.bounding_box()
    await pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, delay=80); await pg.wait_for_timeout(2500)
    sel = "[...document.querySelectorAll('button')].find(e=>e.offsetParent&&(e.innerText||'').trim()==='Select')"
    await pg.evaluate("()=>" + sel + ".scrollIntoView({block:'center'})"); await pg.wait_for_timeout(800)
    r = await pg.evaluate("()=>{const r=" + sel + ".getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
    await pg.mouse.click(r[0] + r[2] / 2, r[1] + r[3] / 2, delay=80)
    for _ in range(10):
        await pg.wait_for_timeout(2500); await click_dialogs(pg)
        if len(bounds) > 1: break
    pg.remove_listener("response", on)
    return bounds
async def main():
    res = json.load(open(RES)) if os.path.exists(RES) else {}
    out0, back0 = dt.date.fromisoformat(OUT_D), dt.date.fromisoformat(BACK_D)
    r = {}
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/svprof", headless=False, executable_path=EXE,
                                                         no_viewport=True, locale="en-US")
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        for shift in range(3):                               # next day(s) if a leg has no non-stop flight
            out = out0 + dt.timedelta(shift) if "out" not in r else out0 + dt.timedelta(r["out"]["shifted_days"])
            back = back0 + dt.timedelta(shift) if "back" not in r else back0 + dt.timedelta(r["back"]["shifted_days"])
            b = await search(pg, out, back)
            for key, resp, frm, to, day, base in (("out", b[0], "DXB", AP, out, out0), ("back", b[-1] if len(b) > 1 else None, AP, "DXB", back, back0)):
                if key in r or resp is None: continue
                fl = nonstop(resp, frm, to)
                if fl: r[key] = {"date": day.isoformat(), "shifted_days": (day - base).days,
                                 "lowest": min(x["from"] for x in fl), "highest": max(x["from"] for x in fl), "flights": fl}
            if "out" in r and "back" in r: break
        await ctx.close()
    res[AP] = r; json.dump(res, open(RES, "w"), indent=1)
    for k in ("out", "back"):
        x = r.get(k, {}); print(AP, k, x.get("date"), x.get("lowest"), x.get("highest"), [(f["flight"], f["dep"], f["from"]) for f in x.get("flights", [])])
asyncio.run(main())
