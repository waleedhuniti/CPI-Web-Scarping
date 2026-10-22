"""PIA (piac.com.pk -> Crane IBE book-pia.crane.aero), return search, 1 adult, economy, direct PK flights.
Per leg: each flight's cheapest economy fare (the ECONOMY price on the card = LITE brand); lowest/highest over flights.
Fare brands (LITE/STANDARD/FREEDOM) are recorded too. Cloudflare is passed by Scrapling's StealthyFetcher (headful, run under xvfb-run).
If the return day has no flight, the next day is tried.
usage: xvfb-run -a python3 air_pia.py DXB ISB 2026-11-01 2026-11-06 air_pia_res.json"""
import sys, json, datetime as dt
from scrapling.fetchers import StealthyFetcher
ORG, DST, OUT_D, BACK_D, RES = sys.argv[1:6]
def url(out, back):
    f = lambda d: d.strftime("%d%%20%b%%20%Y")
    return ("https://book-pia.crane.aero/ibe/availability/?currency=AED&lang=en&tripType=ROUND_TRIP"
            f"&depPort={ORG}&arrPort={DST}&departureDate={f(out)}&returnDate={f(back)}"
            "&passengerQuantities%5B0%5D.passengerType=ADULT&passengerQuantities%5B0%5D.quantity=1"
            "&passengerQuantities%5B1%5D.passengerType=CHILD&passengerQuantities%5B1%5D.quantity=0"
            "&passengerQuantities%5B2%5D.passengerType=INFANT&passengerQuantities%5B2%5D.quantity=0"
            "&availabilityParametricLinkRequestParams=0&withCalendar=false")
CARDS = """() => [...document.querySelectorAll('.js-fare-box')].map(fb => {
  let c = fb; for (let i = 0; i < 8 && c && !/PK-\\d+/.test(c.innerText.replace(fb.innerText, '')); i++) c = c.parentElement;
  const t = c ? c.innerText : '';
  return {num: (t.match(/PK-\\d+/) || [''])[0], times: t.match(/\\d\\d:\\d\\d [AP]M/g) || [], direct: /Direct/.test(t),
          label: (fb.querySelector('.flight-card__fare-label') || {}).innerText || '',
          price: (fb.querySelector('.flight-card__fare-value') || {}).innerText || ''};
})"""
def grab(out, back):
    got = {}
    def act(page):
        page.wait_for_timeout(10000)
        got["text"] = page.inner_text("body")
        got["cards"] = page.evaluate(CARDS)
        brands = []
        for i in range(page.locator("a.js-fare-box").count()):        # expand each fare box to read the brand prices
            try:
                page.locator("a.js-fare-box").nth(i).click(timeout=5000); page.wait_for_timeout(1500)
                brands.append(page.evaluate("""() => [...document.querySelectorAll('.js-select-package')].filter(b => b.offsetParent).map(b => {
                    let c = b.parentElement; while (c && (c.innerText.match(/Total per person/g) || []).length < 1) c = c.parentElement;
                    const m = c && c.innerText.match(/Total per person\\s*([\\d,.]+) AED/); return [b.innerText.replace('Select ', ''), m ? m[1] : null]; })"""))
            except Exception as e:
                brands.append([])
        got["brands"] = brands
    StealthyFetcher.fetch(url(out, back), headless=False, wait=3000, solve_cloudflare=True, network_idle=True, timeout=120000, page_action=act)
    return got
def split(got):
    t = got["text"]; i = t.find("Your return ticket prices")
    cards = [dict(c, brands=(got["brands"][k] if k < len(got["brands"]) else [])) for k, c in enumerate(got["cards"])]
    out, back = [], []
    # cards whose flight number appears before the return-section banner are outbound
    for c in cards:
        if not c["direct"] or "ECONOMY" not in c["label"].upper() or not c["price"]: continue
        rec = {"flight": c["num"], "dep": c["times"][0] if c["times"] else "", "from": float(c["price"].replace(",", "")),
               "brands": {b: float(p.replace(",", "")) for b, p in c["brands"] if p}}
        (out if 0 <= t.find(c["num"]) < i else back).append(rec)
    return out, back
d = lambda s: dt.datetime.strptime(s, "%Y-%m-%d")
res = {}
o, b = d(OUT_D), d(BACK_D)
for shift in range(3):
    got = grab(o, b + dt.timedelta(shift))
    out, back = split(got)
    if shift == 0: res["out"] = out
    if back: res["back"] = back; res["back_date"] = (b + dt.timedelta(shift)).strftime("%Y-%m-%d"); res["back_shift"] = shift; break
def summ(fl, date, shift):
    return {"date": date, "shifted_days": shift, "lowest": min(f["from"] for f in fl) if fl else None,
            "highest": max(f["from"] for f in fl) if fl else None, "flights": fl}
r = {"out": summ(res.get("out", []), OUT_D, 0), "back": summ(res.get("back", []), res.get("back_date"), res.get("back_shift"))}
allres = {}
try: allres = json.load(open(RES))
except Exception: pass
allres[DST] = r; json.dump(allres, open(RES, "w"), indent=1)
print(json.dumps(r, indent=1))
