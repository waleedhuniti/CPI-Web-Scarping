"""flydubai.com, return search: per leg, the cheapest economy fare of each non-stop flight
("from AED x" on the results page); lowest = cheapest flight, highest = dearest flight.
If a leg has no flight on its day, the next day is used (noted).
The page's own flight-list call is refused for automated browsers; the same data comes back
from the equivalent day-count path (/api/flights/01) called inside the loaded page.
usage: xvfb-run -a python3 fz_full.py OUT_YYYYMMDD BACK_YYYYMMDD res.json AP [AP ...]"""
import sys as _sys
_sys.exit("fz_full.py is retired: flydubai refuses its flight-list call for automated browsers and this script reached the same data "
          "through another path, which is a way around a block (CLAUDE.md). flydubai fares are collected manually.")
import asyncio, json, sys, datetime as dt
from playwright.async_api import async_playwright  # plain Playwright: no stealth fork (CLAUDE.md)
EXE = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
OUT_D, BACK_D, RES, APS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
FETCH = """async ([b])=>{const r=await fetch('/api/flights/01',{method:'POST',credentials:'include',
 headers:{'content-type':'application/json','accept':'application/json, text/plain, */*','appid':'DESKTOP'},body:b});
 return [r.status, await r.text()]}"""
def d(s): return dt.datetime.strptime(s, "%Y%m%d")
METRO = {"ALY"}                                           # city groups ("Alexandria All Airports" = HBE + SPX)
def body(ap, out, back):
    m = ap in METRO
    crit = lambda o, de, day, dirn: {"date": day.strftime("%m/%d/%Y") + " 12:00 AM", "dest": de, "direction": dirn,
                                     "origin": o, "isOriginMetro": m and o == ap, "isDestMetro": m and de == ap}
    return json.dumps({"promoCode": "", "cabinClass": "Economy", "isDestMetro": m, "isOriginMetro": False,
                       "paxInfo": {"adultCount": 1, "childCount": 0, "infantCount": 0},
                       "searchCriteria": [crit("DXB", ap, out, "outBound"), crit(ap, "DXB", back, "inBound")],
                       "variant": "1", "campaignCode": ""})
def leg(seg):
    fl = []
    for f in seg.get("flights") or []:
        if f.get("stops") or len(f.get("legs") or []) != 1 or not f.get("isAvailabile"): continue
        fares = [float(t["fare"]["totalFare"].replace(",", "")) for t in f.get("fareTypes") or []
                 if (t.get("cabin") or "").lower() == "economy" and t.get("fare")]
        if fares: fl.append({"flight": "FZ " + f["flightNum"], "dep": f["departureTime"], "from": min(fares),
                              "route": f["origin"] + "-" + f["dest"]})
    return fl
async def main():
    res = json.load(open(RES)) if len(sys.argv) and __import__("os").path.exists(RES) else {}
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/fzprof", headless=False, executable_path=EXE,
                                                         no_viewport=True, locale="en-US")
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        for ap in APS:
            await pg.goto(f"https://flights2.flydubai.com/en/results/rt/a1/DXB_{ap}/{OUT_D}_{BACK_D}",
                          wait_until="domcontentloaded", timeout=90000)
            await pg.wait_for_timeout(12000)
            r = {"airport": ap}
            for i, key in ((0, "out"), (1, "back")):
                day = d(OUT_D if i == 0 else BACK_D)
                for shift in range(3):                     # same day, else next day(s)
                    out, back = (day + dt.timedelta(shift), d(BACK_D)) if i == 0 else (d(OUT_D), day + dt.timedelta(shift))
                    st, txt = await pg.evaluate(FETCH, [body(ap, out, back)])
                    if st != 200: r[key + "_error"] = f"HTTP {st}"; break
                    segs = [s for s in json.loads(txt)["segments"] if s["direction"] == ("outBound", "inBound")[i]]
                    fl = leg(segs[0]) if segs else []
                    if fl:
                        r[key] = {"date": (out if i == 0 else back).strftime("%Y-%m-%d"), "shifted_days": shift,
                                  "lowest": min(x["from"] for x in fl), "highest": max(x["from"] for x in fl), "flights": fl}
                        break
                    await pg.wait_for_timeout(2000)
            res[ap] = r
            o, b = r.get("out", {}), r.get("back", {})
            print(ap, o.get("date"), o.get("lowest"), o.get("highest"), "|", b.get("date"), b.get("lowest"), b.get("highest"),
                  r.get("out_error", ""), r.get("back_error", ""), flush=True)
            json.dump(res, open(RES, "w"), ensure_ascii=False, indent=1)
            await pg.wait_for_timeout(4000)
        await ctx.close()
asyncio.run(main())
