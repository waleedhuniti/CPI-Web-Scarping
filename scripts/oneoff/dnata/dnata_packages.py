"""One-off: dnata package prices (flight + hotel) for the hotels of the monthly package sheet.
Stay CHECKIN..CHECKOUT, 1 adult from DXB, Emirates non-stop both ways, Bed & Breakfast if the hotel offers it, else the cheapest board.
Runs in a headless browser (the site's own GraphQL calls, made from the page) and writes results JSON."""
import asyncio, json, sys, re
from playwright.async_api import async_playwright
import os
CHECKIN, CHECKOUT = os.environ.get("CHECKIN", "2026-10-25"), os.environ.get("CHECKOUT", "2026-10-29")
Q = json.load(open("queries.json"))
TARGETS = json.load(open(sys.argv[1]))          # [{row, city, term, keys, estab (optional: pin a dnata hotel id)}]
OUT = sys.argv[2]

JS = """async ([op, query, variables]) => {
  const r = await fetch('/graphql/' + op.toLowerCase(), {method: 'POST', headers: {'content-type': 'application/json', 'apollographql-client-name': 'Dnatatravel', 'apollographql-client-version': '0.1.0', 'x-mock-errors-enabled': 'false', 'x-original-origin': 'www-hcw.pd.dnatatravel.com', 'accept': '*/*', 'x-trp-correlation-id': crypto.randomUUID()},
                        body: JSON.stringify({operationName: op, variables, query})});
  return [r.status, await r.text()];
}"""

async def gql(pg, op, variables):
    for attempt in range(3):
        st, body = await pg.evaluate(JS, [op, Q[op], variables])
        if st == 200:
            d = json.loads(body)
            if d.get("errors"): raise RuntimeError(f"{op}: {d['errors'][0].get('message','')[:200]}")
            return d["data"]
        await pg.wait_for_timeout(4000)
    raise RuntimeError(f"{op}: HTTP {st} {body[:200]}")

def norm(s): return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower().replace("ö", "o"))

async def main():
    res = json.load(open(OUT)) if len(sys.argv) > 3 else {}
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        ctx = await b.new_context(locale="en-US", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        pg = await ctx.new_page()
        await pg.goto("https://www.dnatatravel.com/", wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(6000)
        trips = {}
        for t in TARGETS:
            key = str(t["row"])
            if key in res and res[key].get("total"): continue
            r = {"row": t["row"], "city": t["city"], "sheet_name": t["sheet_name"]}
            try:
                if t["city"] not in trips:
                    d = await gql(pg, "DestinationAutocompleter", {"request": {"searchTerm": t["city"], "maxResults": 15, "holidaySearch": True}})
                    dests = d["destinationAutocompleterResults"]["destinations"] or []
                    dest = next((x for x in dests if norm(x["title"]).strip() == norm(t["city"]).strip()), dests[0] if dests else None)
                    if not dest: raise RuntimeError("destination not found")
                    did = dest["destinationId"]
                    seen = {}
                    async def grab(resp):
                        if resp.url.endswith("/graphql/holidaysearch"):
                            try: seen["trip"] = json.loads(await resp.text())["data"]["holidaySearch"]["tripStateId"]
                            except Exception: pass
                        if resp.url.endswith("/graphql/hotelsearchresults"): seen["hotels"] = True
                    pg.on("response", grab)
                    url = (f"https://www.dnatatravel.com/holidays/hotels?checkIn={CHECKIN}&checkOut={CHECKOUT}&destIds={did}&tripType=HOLIDAY"
                           f"&rooms.0.adults=1&depAirports=DXB&adults=1&cabin=1&dateSearchType=CHOOSE_DATE&priceDisplayMode=2&sort=PRICE_LOWEST_FIRST")
                    await pg.goto(url, wait_until="domcontentloaded", timeout=90000)
                    for i in range(30):
                        await pg.wait_for_timeout(2000)
                        if seen.get("trip") and seen.get("hotels"): break
                    pg.remove_listener("response", grab)
                    if not seen.get("trip"): raise RuntimeError("search did not start")
                    trips[t["city"]] = (seen["trip"], f"{dest['title']}, {dest.get('subTitle','')}", did)
                trip, dtitle, did = trips[t["city"]]
                r["destination"] = f"{dtitle} ({did})"
                async def hotels(board):
                    cb = [{"id": "boardTypes", "selectedIds": [board]}] if board else []
                    v = {"paging": {"limit": 50, "offset": 0, "pagingType": 1}, "tripStateId": trip,
                         "filters": {"checkboxFilters": cb, "rangeFilters": [], "textFilter": [{"id": "hotelName", "value": t["term"]}]},
                         "sortCriterion": "PRICE_LOWEST_FIRST", "departureDateFormat": "FULLDATE", "timeFormat": "TIME", "currencyFormat": "ROUNDED"}
                    for i in range(6):
                        d = await gql(pg, "HotelSearchResults", v)
                        hs = d["hotelSearchResults"]["hotels"] or []
                        if hs: return hs
                        await pg.wait_for_timeout(3000)             # results may still be loading on the server
                    return []
                def pick(hs):
                    if t.get("estab"):                       # pinned: the same dnata hotel as the earlier file
                        ok = [h for h in hs if str(h["hotel"]["estabId"]) == str(t["estab"])]
                    else:
                        ok = [h for h in hs if all(k in norm(h["hotel"]["name"]) for k in t["keys"]) and not any(x in norm(h["hotel"]["name"]) for x in t.get("exclude", []))]
                    if not ok: r.setdefault("seen_names", []).extend(h["hotel"]["name"] for h in hs[:8])
                    return ok[0] if ok else None
                h = pick(await hotels("2"))
                r["board_rule"] = "Bed & Breakfast"
                if not h:
                    h = pick(await hotels(None)); r["board_rule"] = "cheapest (no B&B)"
                if not h:
                    r["note"] = "hotel not found on dnata for these dates"; res[key] = r; json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1); print(key, r["note"]); continue
                ps = h["pricingSummary"]
                r.update(hotel_found=h["hotel"]["name"], estab_id=h["hotel"]["estabId"], stars=h["hotel"].get("starRating"),
                         board=ps["boardTypeDescription"], package_default=ps["price"])
                fo = h.get("flight") or {}
                r["default_flight"] = " / ".join(s["airline"]["name"] for leg in ("outboundLeg", "inboundLeg") for s in ((fo.get(leg) or {}).get("segments") or []))
                seen2 = {}
                async def grab2(resp):
                    if resp.url.endswith("/graphql/hotelbasketsummaryresults"): seen2["ok"] = True
                pg.on("response", grab2)
                await pg.goto(f"https://www.dnatatravel.com/holidays/hotels/{h['hotel']['estabId']}?checkIn={CHECKIN}&checkOut={CHECKOUT}&destIds={did}"
                              f"&tripType=HOLIDAY&rooms.0.adults=1&depAirports=DXB&adults=1&cabin=1&dateSearchType=CHOOSE_DATE&priceDisplayMode=2&tripId={trip}",
                              wait_until="domcontentloaded", timeout=90000)
                for i in range(25):
                    await pg.wait_for_timeout(2000)
                    if seen2.get("ok"): break
                pg.remove_listener("response", grab2)
                await pg.wait_for_timeout(2000)
                fv = {"paging": {"pageIndex": 0, "pageSize": 50}, "tripStateId": trip, "departureDateFormat": "FULLDATE", "timeFormat": "TIME", "currencyFormat": "ROUNDED",
                      "filters": {"checkboxFilters": [{"id": "stop", "selectedIds": ["0"]}, {"id": "airline", "selectedIds": ["Emirates"]}], "rangeFilters": [], "textFilter": []},
                      "sortCriterion": "PRICE_LOWEST_FIRST", "hotelCheckInDate": CHECKIN + "T00:00:00", "estabId": int(h["hotel"]["estabId"])}
                fl = (await gql(pg, "FlightSearchResults", fv))["flightSearchResults"]["flights"] or []
                def ok(f):
                    segs = f["outboundLeg"]["segments"] + f["inboundLeg"]["segments"]
                    return len(f["outboundLeg"]["segments"]) == 1 and len(f["inboundLeg"]["segments"]) == 1 and all(s["airline"]["code"] == "EK" for s in segs)
                fl = [f for f in fl if ok(f)]
                if not fl:
                    r["note"] = "no Emirates non-stop flight offered with this hotel"
                else:
                    f = min(fl, key=lambda f: f["deltaPrice"])
                    r.update(flight=f"{f['outboundLeg']['segments'][0]['flightNumber']} {f['outboundLeg']['segments'][0]['departureDateTime']['time']} / "
                                    f"{f['inboundLeg']['segments'][0]['flightNumber']} {f['inboundLeg']['segments'][0]['departureDateTime']['time']}",
                             flight_delta=round(f["deltaPrice"], 2), total=round(ps["price"] + f["deltaPrice"], 2))
            except Exception as e:
                r["note"] = f"error: {e}"[:250]
            res[key] = r
            json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
            print(key, r.get("hotel_found"), r.get("board"), r.get("total"), r.get("note", ""), flush=True)
            await pg.wait_for_timeout(2500)
        await b.close()
asyncio.run(main())
