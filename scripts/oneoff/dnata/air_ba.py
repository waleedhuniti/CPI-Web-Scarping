"""British Airways (britishairways.com), return search DXB -> LHR -> DXB, 1 adult, economy.
Opens BA's own search deep link once, the way a visitor does, and records what the page loads:
- the fare calendar (calendars-air): the lowest fare per departure day for the outbound leg, in AED;
- the flight list (offer-flight/oneway/outbound): every flight with its fares.
On 2026-10-26 the flight list came back as BA's "technical difficulties" information page for this server, so only the
calendar's lowest fare is available; no highest fare and no return-leg prices (the return calendar loads only after an
outbound flight is chosen).
usage: xvfb-run -a python3 air_ba.py OUT_YYYY-MM-DD BACK_YYYY-MM-DD res.json"""
import asyncio, json, sys
from patchright.async_api import async_playwright
OUT_D, BACK_D, RES = sys.argv[1:4]
URL = ("https://www.britishairways.com/nx/b/airselect/en/are/book/search/?trip=return"
       f"&departureDate={OUT_D}&returnDate={BACK_D}&from=DXB&to=LHR&travelClass=economy&adults=1&youngAdults=0&children=0&infants=0")
async def main():
    got = {}
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/baprof", headless=False, no_viewport=True, locale="en-US",
                                                         executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        pg = ctx.pages[0]
        async def on(r):
            if "/bff/offer-flight/" in r.url:
                try: got[r.url] = (r.status, await r.text())
                except Exception: pass
        pg.on("response", on)
        await pg.goto(URL, wait_until="commit", timeout=90000)
        await pg.wait_for_timeout(35000)
        page = await pg.inner_text("body")
        await ctx.close()
    res = {"LHR": {"url": URL, "currency": "AED"}}
    r = res["LHR"]
    for u, (st, body) in got.items():
        if "calendars-air" in u and "from=DXB" in u:
            cal = {x["date"]: x["amount"] for x in json.loads(body)["result"] if x.get("status") == "AVAILABLE"}
            r["out_calendar"] = cal
            if OUT_D in cal:
                r["out"] = {"date": OUT_D, "shifted_days": 0, "lowest": float(cal[OUT_D]), "highest": None, "flights": [],
                            "source": "fare calendar (lowest fare of the day)"}
        if "/oneway/outbound" in u:
            try:
                data = json.loads(body); r["out_list_raw"] = data
            except ValueError:
                r["out_list_error"] = f"HTTP {st}: BA information page instead of the flight list"
    if "technical difficulties" in page:
        r["page_message"] = "Sorry, we're having technical difficulties (shown instead of the flight list)"
    r.setdefault("back", None)
    r["back_note"] = "return-leg prices load only after an outbound flight is selected; not reached"
    json.dump(res, open(RES, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in r.items() if k != "out_list_raw"}, ensure_ascii=False)[:800])
asyncio.run(main())
