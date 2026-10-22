"""Royal Jordanian (rj.com), return search, 1 adult, economy: per leg, each non-stop RJ flight's cheapest
economy fare (Saver/Value/Flex); lowest = cheapest flight, highest = dearest flight.
Fills the rj.com search form, reads the booking engine's FlexPricerAvailability JSON.
If a leg has no flight on its day, the next day is searched (noted as shifted_days).
usage: xvfb-run -a python3 air_rj.py 2026-11-01 2026-11-06 air_rj_res.json AMM"""
import asyncio, json, sys, datetime as dt
from collections import defaultdict
from patchright.async_api import async_playwright
EXE = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
OUT_D, BACK_D, RES, DEST = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
def lbl(d): return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")      # flatpickr aria-label
async def search(ctx, out, back):
    pg = ctx.pages[0]; cap = {}
    async def on(r):
        if "FlexPricerAvailability" in r.url:
            try: cap["json"] = json.loads(await r.text())
            except Exception: pass
    pg.on("response", on)
    await pg.goto("https://www.rj.com/en", wait_until="domcontentloaded", timeout=60000); await pg.wait_for_timeout(8000)
    await pg.click("#bw-origin-1-ts-control"); await pg.keyboard.type("DXB", delay=150); await pg.wait_for_timeout(2500)
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
    await pg.focus("#bw-destination-1-ts-control"); await pg.wait_for_timeout(1500)
    await pg.keyboard.type(DEST, delay=200); await pg.wait_for_timeout(3000)
    opt = await pg.evaluate("(c)=>{const o=[...document.querySelectorAll('#bw-destination-1-ts-dropdown .option')].find(e=>e.dataset.value===c||e.innerText.includes(c));return o?o.id:null}", DEST)
    if not opt: raise RuntimeError("destination not in RJ route list")
    await pg.click("#" + opt); await pg.wait_for_timeout(1500)
    await pg.click("#bw-departure-return-1"); await pg.wait_for_timeout(1500)
    for d in (out, back):
        await pg.locator(f'.flatpickr-day[aria-label="{lbl(d)}"]:visible').first.click(); await pg.wait_for_timeout(800)
    await pg.keyboard.press("Escape"); await pg.mouse.click(30, 300); await pg.wait_for_timeout(1000)
    await pg.locator(".bw-submit-btn:visible").first.click()
    for _ in range(25):
        await pg.wait_for_timeout(2000)
        if "json" in cap: break
    pg.remove_listener("response", on)
    if "json" not in cap: raise RuntimeError("no availability response")
    A = cap["json"]["data"]["pageDefinitionConfig"]["pageData"]["business"]["Availability"]
    legs = []
    for bi, pb in enumerate(A["proposedBounds"]):
        flights = {}
        for g in pb["proposedFlightsGroup"]:
            s = g["segments"]
            if len(s) != 1 or s[0].get("nbrOfStops") or s[0]["airline"]["code"] != "RJ": continue
            flights[g["proposedBoundId"]] = {"flight": "RJ " + s[0]["flightNumber"],
                                             "dep": str(dt.datetime.strptime(s[0]["beginDate"], "%b %d, %Y %I:%M:%S %p"))}
        fares = defaultdict(dict)
        for r in A["recommendationList"]:
            b = r["bounds"][bi]
            if not b["ffCode"].startswith("EC"): continue
            for fg in b["flightGroupList"]:
                fares[fg["flightId"]][b["ffCode"]] = min(fares[fg["flightId"]].get(b["ffCode"], 1e9), b["boundAmount"]["totalAmount"])
        fl = [dict(flights[i], **{"from": min(f.values()), "fares": f}) for i, f in fares.items() if i in flights]
        legs.append(sorted(fl, key=lambda x: x["dep"]))
    return legs
async def main():
    o0, b0 = dt.date.fromisoformat(OUT_D), dt.date.fromisoformat(BACK_D)
    res = {}
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/rjprof", headless=False, executable_path=EXE, no_viewport=True, locale="en-US")
        r = {}
        for shift in range(3):                                   # shift the return day only if it has no flight
            legs = await search(ctx, o0, b0 + dt.timedelta(shift))
            if "out" not in r and legs[0]:
                r["out"] = {"date": str(o0), "shifted_days": 0, "flights": legs[0]}
            if legs[1]:
                r["back"] = {"date": str(b0 + dt.timedelta(shift)), "shifted_days": shift, "flights": legs[1]}; break
        for k in ("out", "back"):
            if k in r:
                v = [f["from"] for f in r[k]["flights"]]; r[k]["lowest"], r[k]["highest"] = min(v), max(v)
        res[DEST] = r
        await ctx.close()
    json.dump(res, open(RES, "w"), ensure_ascii=False, indent=1)
    for k in ("out", "back"):
        x = res[DEST].get(k, {}); print(k, x.get("date"), x.get("lowest"), x.get("highest"), [(f["flight"], f["dep"][11:16], f["from"]) for f in x.get("flights", [])])
asyncio.run(main())
