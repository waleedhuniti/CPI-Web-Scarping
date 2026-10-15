import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta, date
from bs4 import BeautifulSoup

URL = "https://tradingeconomics.com/commodities"
M = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
KEYS = {"price": "price", "chg": "change", "%chg": "pct", "weekly": "weekly", "monthly": "monthly", "ytd": "ytd", "yoy": "yoy", "date": "price_date"}
COLS = ["category", "commodity", "unit", "price", "change", "pct", "weekly", "monthly", "ytd", "yoy", "price_date"]

def num(s):
    try: return float(re.sub(r"[,%\s]", "", str(s)))
    except ValueError: return None

def iso(label, today):
    m = re.fullmatch(r"([A-Za-z]{3})/(\d{1,2})", (label or "").strip())
    if not m or m.group(1) not in M: return None
    d = date(today.year, M[m.group(1)], int(m.group(2)))
    if (d - today).days > 2: d = d.replace(year=today.year - 1)
    return d.isoformat()

def parse(html, today):
    soup = BeautifulSoup(html, "html.parser"); rows = []
    for t in soup.find_all("table"):
        h = [th.get_text(strip=True) for th in t.select("thead th")]
        if len(h) < 2 or h[1] != "Price": continue
        for tr in t.select("tbody tr"):
            tds = tr.find_all("td")
            if not tds or not tds[0].find("b"): continue
            r = {"category": h[0], "commodity": tds[0].find("b").get_text(strip=True),
                 "unit": (tds[0].find("div").get_text(strip=True) if tds[0].find("div") else None)}
            for i, x in enumerate(h[1:], 1):
                k = KEYS.get(x.lower())
                if not k or i >= len(tds): continue
                txt = " ".join(tds[i].get_text().split())
                r[k] = iso(txt, today) if k == "price_date" else num(tds[i].get("data-value", txt))
            rows.append([r.get(c) for c in COLS])
    return rows

if __name__ == "__main__":
    now = datetime.now(timezone.utc); dubai = now + timedelta(hours=4)
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        html = open(src, encoding="utf-8").read(); method = "apify/web-fetch"
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore"); method = "direct fetch + BeautifulSoup"
    rows = parse(html, dubai.date())
    if len(rows) < 80:
        print(f"ERROR: only {len(rows)} rows parsed", file=sys.stderr); sys.exit(2)
    doc = {"run_date": dubai.date().isoformat(), "scraped_at": now.isoformat(timespec="seconds"),
           "source": URL, "method": method, "cols": COLS, "rows": rows}
    out = f"te_{doc['run_date']}.json"
    json.dump(doc, open(out, "w"))
    print(out, len(rows), "rows")
