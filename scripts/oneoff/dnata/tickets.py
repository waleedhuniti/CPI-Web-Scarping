"""Flight-only fares from dnata: per route and journey (out 1 Nov, back 6 Nov, return 1-6 Nov), direct flights, 1 adult economy:
lowest and highest fare per airline (the airline flying every segment)."""
import asyncio, json, re, sys, os
from playwright.async_api import async_playwright
Q = json.load(open("queries.json"))
OUT = sys.argv[2]; JOBS = json.load(open(sys.argv[1]))
JS = """async ([op, query, variables]) => {
  const r = await fetch('/graphql/' + op.toLowerCase(), {method: 'POST', headers: {'content-type': 'application/json', 'apollographql-client-name': 'Dnatatravel', 'apollographql-client-version': '0.1.0', 'x-mock-errors-enabled': 'false', 'x-original-origin': 'www-hcw.pd.dnatatravel.com', 'accept': '*/*', 'x-trp-correlation-id': crypto.randomUUID()},
                        body: JSON.stringify({operationName: op, variables, query})});
  return [r.status, await r.text()];
}"""
def url(j):
    u = (f"https://www.dnatatravel.com/flights?checkIn={j['out']}&tripType=FLIGHT&depAirports={j['frm']}&adults=1&arrivalAirport={j['to']}"
         f"&cabin=1&dateSearchType=CHOOSE_DATE&flightFilters.stop=0&fsort=PRICE_LOWEST_FIRST")
    return u + (f"&checkOut={j['back']}&flightJourneyType=RETURN" if j.get('back') else "&flightJourneyType=ONEWAY")
async def main():
    res = json.load(open(OUT)) if len(sys.argv) > 3 else {}
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        ctx = await b.new_context(locale="en-US", viewport={"width": 1300, "height": 1000})
        for j in JOBS:
            key = j['key']
            if key in res and res[key].get('airlines'): continue
            pg = await ctx.new_page(); seen = {}
            async def grab(resp):
                if resp.url.endswith('/graphql/flightsearch'):
                    try: seen['trip'] = json.loads(await resp.text())['data']['flightSearch']['tripStateId']
                    except Exception: pass
                if resp.url.endswith('/graphql/flightsearchresults'): seen['res'] = True
            pg.on('response', grab)
            r = {'key': key, 'url': url(j)}
            try:
                await pg.goto(url(j), wait_until='domcontentloaded', timeout=90000)
                for i in range(30):
                    await pg.wait_for_timeout(2000)
                    if seen.get('trip') and seen.get('res'): break
                trip = seen.get('trip') or (re.search(r'tripId=([0-9a-f-]{36})', pg.url) or [None, None])[1]
                if not trip: raise RuntimeError('search did not start')
                flights = []
                for page in range(6):
                    v = {"paging": {"pageIndex": page, "pageSize": 50}, "tripStateId": trip, "departureDateFormat": "FULLDATE", "timeFormat": "TIME",
                         "currencyFormat": "ROUNDED", "filters": {"checkboxFilters": [{"id": "stop", "selectedIds": ["0"]}], "rangeFilters": [], "textFilter": []},
                         "sortCriterion": "PRICE_LOWEST_FIRST"}
                    st, body = await pg.evaluate(JS, ["FlightSearchResults", Q["FlightSearchResults"], v])
                    d = json.loads(body)
                    if d.get('errors'): raise RuntimeError(d['errors'][0].get('message', '')[:200])
                    fr = d['data']['flightSearchResults']; fl = fr['flights'] or []
                    flights += fl
                    r['total_direct'] = fr.get('filteredFlights')
                    if len(fl) < 50: break
                by = {}
                for f in flights:
                    segs = f['outboundLeg']['segments'] + ((f.get('inboundLeg') or {}).get('segments') or [])
                    if any(len(l) != 1 for l in [f['outboundLeg']['segments']] + ([f['inboundLeg']['segments']] if f.get('inboundLeg') else [])): continue
                    codes = {s['airline']['name'] for s in segs}
                    if len(codes) != 1: continue
                    a = codes.pop(); price = f.get('totalPrice') or f.get('pricePerAdult') or f.get('pricePerPerson')
                    fn = ' / '.join(s['flightNumber'] + ' ' + s['departureDateTime']['time'] for s in segs)
                    e = by.setdefault(a, {'min': None, 'max': None, 'n': 0, 'min_flight': '', 'max_flight': ''})
                    e['n'] += 1
                    if e['min'] is None or price < e['min']: e['min'], e['min_flight'] = price, fn
                    if e['max'] is None or price > e['max']: e['max'], e['max_flight'] = price, fn
                r['airlines'] = by
            except Exception as ex:
                r['error'] = f'{type(ex).__name__}: {ex}'[:200]
            res[key] = r; json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
            print(key, r.get('total_direct'), {a: (round(e['min']), round(e['max']), e['n']) for a, e in (r.get('airlines') or {}).items()}, r.get('error', ''), flush=True)
            await pg.close(); await asyncio.sleep(2)
        await b.close()
asyncio.run(main())
