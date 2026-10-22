"""EgyptAir (egyptair.com, UAE point of sale, AED): return search DXB->CAI / CAI->DXB, economy, 1 adult.
Per leg: each non-stop MS flight's cheapest economy fare; lowest = cheapest flight, highest = dearest flight.
The search is started from the egyptair.com home form; the site's own air-bounds call is captured and replayed
in the page for the return bound (and for the next day if a leg has no flight).
usage: xvfb-run -a python3 air_egyptair.py 20261101 20261106 air_egyptair_res.json"""
import asyncio, json, sys, datetime as dt
from patchright.async_api import async_playwright
OUT_D, BACK_D, RES = sys.argv[1:4]
DEST = ("Cairo", "CAI")
P = "ctl00_PlaceHolderMain_ctl00_Switcher_HomePageBooking1_ctl00_"
def d(s): return dt.datetime.strptime(s, "%Y%m%d")
def parse(js, frm, to):
    dic = js.get("dictionaries", {}).get("flight", {})
    fl = []
    for g in js.get("data", {}).get("airBoundGroups", []):
        segs = g["boundDetails"]["segments"]
        if len(segs) != 1: continue                           # non-stop only
        f = dic.get(segs[0]["flightId"], {})
        if f.get("operatingAirlineCode") != "MS" or f["departure"]["locationCode"] != frm or f["arrival"]["locationCode"] != to: continue
        eco = [b["prices"]["totalPrices"][0]["total"] for b in g["airBounds"]
               if all(a.get("cabin") == "eco" for a in b["availabilityDetails"])]
        if eco: fl.append({"flight": "MS " + f["marketingFlightNumber"], "dep": f["departure"]["dateTime"][:16], "from": float(min(eco))})
    return fl
REPLAY = """async ([u, h, b]) => { const r = await fetch(u, {method: 'POST', headers: h, body: b}); return [r.status, await r.text()]; }"""
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/msprof", headless=False, no_viewport=True, locale="en-US",
                                                         executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        pg = ctx.pages[0]; cap = {}
        async def on(r):
            if r.url.endswith("/v2/search/air-bounds") and "req" not in cap:
                cap["url"] = r.url; cap["req"] = r.request.post_data; cap["hdr"] = await r.request.all_headers()
                cap["resp"] = await r.text()
        ctx.on("response", on)
        await pg.goto("https://www.egyptair.com/en/Pages/Default.aspx", wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(8000)
        async def city(field, txt, code):
            await pg.locator(f"#{P}ucCountry_1_{field}").click()
            await pg.keyboard.press("Control+A"); await pg.keyboard.press("Backspace")
            await pg.keyboard.type(txt, delay=150); await pg.wait_for_timeout(2500)
            await pg.locator(f'#tat_table tr:has-text("({code})")').first.click(); await pg.wait_for_timeout(1000)
        await city("txtFromCity", "Dubai", "DXB"); await city("txtToCity", *DEST)
        fmt = lambda s: d(s).strftime("%d %B %Y")
        await pg.evaluate(f"""() => {{ document.getElementById('{P}ucDepTime_1_rdpCalender').value = '{fmt(OUT_D)}';
            document.getElementById('{P}ucReturnDate_rdpCalender').value = '{fmt(BACK_D)}';
            document.getElementById('{P}HF_selectedCountryCode_refxIntegration').value = 'AE'; }}""")
        await pg.locator(f'input[name="ctl00$PlaceHolderMain$ctl00$Switcher$HomePageBooking1$ctl00$buSubmit"]').click()
        for _ in range(30):
            await pg.wait_for_timeout(2000)
            if "resp" in cap: break
        if "resp" not in cap: raise SystemExit("search did not return air-bounds")
        hdr = {k: v for k, v in cap["hdr"].items() if k in ("authorization", "content-type", "accept") or k.startswith(("x-", "ama-"))}
        print("replay headers:", sorted(hdr))
        base = json.loads(cap["req"]); res = {"CAI": {}}
        for i, key, frm, to in ((0, "out", "DXB", DEST[1]), (1, "back", DEST[1], "DXB")):
            for shift in range(3):
                body = json.loads(json.dumps(base))
                its = body["itineraries"]
                for j, it in enumerate(its): it["isRequestedBound"] = (j == i)
                day = d((OUT_D, BACK_D)[i]) + dt.timedelta(shift)
                its[i]["departureDateTime"] = day.strftime("%Y-%m-%dT00:00:00.000")
                st, txt = await pg.evaluate(REPLAY, [cap["url"], hdr, json.dumps(body)])
                if st != 200: res["CAI"][key + "_error"] = f"HTTP {st}: {txt[:200]}"; break
                fl = parse(json.loads(txt), frm, to)
                if fl:
                    res["CAI"][key] = {"date": day.strftime("%Y-%m-%d"), "shifted_days": shift, "currency": "AED",
                                       "lowest": min(x["from"] for x in fl), "highest": max(x["from"] for x in fl),
                                       "flights": sorted(fl, key=lambda x: x["dep"])}
                    break
                await pg.wait_for_timeout(2000)
        res["CAI"]["source"] = "egyptair.com (UAE point of sale), searched " + dt.date.today().isoformat()
        json.dump(res, open(RES, "w"), ensure_ascii=False, indent=1)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        await ctx.close()
asyncio.run(main())
