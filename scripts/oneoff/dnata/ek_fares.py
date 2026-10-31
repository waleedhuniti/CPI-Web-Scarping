"""Emirates economy fares from emirates.com, one one-way search per leg (DXB -> city on the out date, city -> DXB on the back date).
Meant for a normal home or office connection: from cloud servers emirates.com refuses the search ("access restricted").

usage: python ek_fares.py <out YYYY-MM-DD> <back YYYY-MM-DD> <ek_res.json> [AP ...]   (default: every route of the tickets sheet)

A visible browser opens (Scrapling's stealth Chromium; --real-chrome uses the installed Google Chrome instead). If Emirates shows
a human check, do it yourself in that window: the script waits up to 3 minutes for the results, it never solves checks.
Output, like fz_full.py: {AP: {"out": {date, lowest, highest, flights: [{flight, dep, from}]}, "back": {...}}}, or {"error": ...}.
Each search also leaves ek_debug/<AP>_<leg>.png / .html / .txt (the page text the fares were read from) for checking.
"""
import json
import os
import re
import sys
import time

from scrapling.fetchers import StealthySession

ROUTES = ["DEL", "LHR", "RUH", "KHI", "JFK", "CMB", "BKK", "IST", "CAI", "AMM"]
HOME = "https://www.emirates.com/ae/english/"
DEBUG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ek_debug")
PRICE = re.compile(r"AED\s*([\d,]+(?:\.\d+)?)")
FLIGHT = re.compile(r"\bEK\s?(\d{1,4})\b")
CHECK = re.compile(r"(?i)press\s*(?:&|and)\s*hold|verify you are (?:a )?human|are you a robot|captcha|unusual traffic")


def pick_airport(page, name, code):
    click_box(page, f'input[name="{name}"]')
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(code, delay=120)
    page.wait_for_timeout(1500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)


def click_box(page, selector, text=None):
    """Click the first element of the selector that has a size on screen (the page holds hidden copies of every widget)."""
    boxes = page.evaluate("""([sel, text]) => [...document.querySelectorAll(sel)]
        .filter(e => !text || e.innerText.includes(text))
        .map(e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })
        .filter(b => b[2] > 0 && b[3] > 0)""", [selector, text])
    if not boxes:
        raise RuntimeError(f"nothing visible for {selector} {text or ''}")
    x, y, w, h = boxes[0]
    page.mouse.click(x + w / 2, y + h / 2)


def search(page, frm, to, day, tag, res):
    try:
        _search(page, frm, to, day, tag, res)
    except Exception:
        os.makedirs(DEBUG, exist_ok=True)
        page.screenshot(path=os.path.join(DEBUG, tag + "_failed.png"))
        open(os.path.join(DEBUG, tag + "_failed.html"), "w", encoding="utf-8").write(page.content())
        raise


def _search(page, frm, to, day, tag, res):
    """Fill the home page widget for a one-way economy search and read the results page."""
    res["stage"] = "form"
    page.wait_for_timeout(2500)
    if "accessrestricted" in page.url or "access is restricted" in page.evaluate("() => document.body ? document.body.innerText : ''"):
        res.update(url="accessrestricted", stage="blocked")
        return
    for t in ("Accept", "Accept all", "Accept All"):
        b = page.get_by_role("button", name=t)
        if b.count():
            try:
                b.first.click(timeout=3000)
                break
            except Exception:
                pass
    pick_airport(page, "Departure airport", frm)
    pick_airport(page, "Arrival airport", to)
    page.wait_for_timeout(1000)
    click_box(page, "label", "One way")                  # the calendar panel's "One way" box
    page.wait_for_timeout(800)
    y, m, d = (int(x) for x in day.split("-"))
    click_box(page, f'button[data-string="{d}{m - 1}{y}"]')   # data-string is day + zero-based month + year
    page.wait_for_timeout(1200)
    os.makedirs(DEBUG, exist_ok=True)
    page.screenshot(path=os.path.join(DEBUG, tag + "_form.png"))
    click_box(page, "button.js-widget-submit", "Search flights")
    res["stage"] = "results"
    text, end = "", time.time() + 180
    while time.time() < end:                            # results, a refusal, or a human check the user does by hand
        page.wait_for_timeout(3000)
        if "accessrestricted" in page.url:
            break
        text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if CHECK.search(text):
            print(f"  {tag}: the site shows a human check - please do it in the browser window", flush=True)
            continue
        if FLIGHT.search(text) and PRICE.search(text):
            page.wait_for_timeout(4000)
            text = page.evaluate("() => document.body.innerText")
            break
    os.makedirs(DEBUG, exist_ok=True)
    page.screenshot(path=os.path.join(DEBUG, tag + ".png"), full_page=True)
    open(os.path.join(DEBUG, tag + ".html"), "w", encoding="utf-8").write(page.content())
    open(os.path.join(DEBUG, tag + ".txt"), "w", encoding="utf-8").write(text)
    res.update(url=page.url, text=text, stage="read")


def fares(text, day):
    """Per flight the cheapest economy price on the card: the page text from one EK flight number to the next."""
    hits = list(FLIGHT.finditer(text))
    flights = []
    for i, h in enumerate(hits):
        part = text[h.start(): hits[i + 1].start() if i + 1 < len(hits) else len(text)]
        eco = part.lower().find("economy")
        prices = PRICE.findall(part[eco:] if eco >= 0 else part)
        if not prices:
            continue
        dep = re.search(r"\b([01]\d|2[0-3]):[0-5]\d\b", part)
        flights.append({"flight": "EK" + h.group(1), "dep": dep.group(0) if dep else "", "from": float(prices[0].replace(",", ""))})
    seen, uniq = set(), []
    for f in flights:                                    # a flight number shown twice (connections, details) counts once
        if f["flight"] not in seen:
            seen.add(f["flight"])
            uniq.append(f)
    if not uniq:
        return None
    lo, hi = min(f["from"] for f in uniq), max(f["from"] for f in uniq)
    return {"date": day, "shifted_days": 0, "lowest": lo, "highest": hi, "flights": uniq}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_d, back_d, dest = args[:3]
    aps = args[3:] or ROUTES
    out = json.load(open(dest, encoding="utf-8")) if os.path.exists(dest) else {}
    with StealthySession(headless=False, real_chrome="--real-chrome" in sys.argv, timeout=120000, network_idle=True) as s:
        for ap in aps:
            if out.get(ap, {}).get("out") and out[ap].get("back"):
                continue                                 # already done in an earlier run
            r = out.get(ap, {})
            for leg, frm, to, day in (("out", "DXB", ap, out_d), ("back", ap, "DXB", back_d)):
                if r.get(leg):
                    continue
                tag, got = f"{ap}_{leg}", {}
                try:
                    s.fetch(HOME, page_action=lambda page: search(page, frm, to, day, tag, got))
                except Exception as e:
                    got["error"] = repr(e)[:300]
                if "accessrestricted" in got.get("url", ""):
                    print("  emirates.com refuses this connection; try again later or from another network", flush=True)
                    r[leg + "_error"] = "emirates.com refused the search (access restricted)"
                elif got.get("error"):
                    r[leg + "_error"] = got["error"]
                elif got.get("stage") != "read":
                    r[leg + "_error"] = f"stopped at the {got.get('stage', 'page load')} step (see the console and ek_debug)"
                else:
                    f = fares(got.get("text", ""), day)
                    if f:
                        r[leg] = f
                    else:
                        r[leg + "_error"] = "no economy fare read from the results page (see ek_debug)"
                print(ap, leg, r.get(leg, {}).get("lowest"), r.get(leg, {}).get("highest"), r.get(leg + "_error", ""), flush=True)
                out[ap] = r
                json.dump(out, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                time.sleep(5)
    print("done:", dest)


if __name__ == "__main__":
    main()
