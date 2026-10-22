"""flydubai.com, return search: lowest fare shown for the outbound day and the return day (the date bar), as the manual team records it."""
import asyncio, re, sys, json
from playwright.async_api import async_playwright
OUT_D, BACK_D = "20261101", "20261106"
ROUTES = json.loads(sys.argv[1]); RES = sys.argv[2]
def day_price(text, label):
    m = re.search(re.escape(label) + r'\s*\n\s*\w+day\s*\n\s*AED\s*([\d,]+)', text)
    return float(m.group(1).replace(',', '')) if m else None
async def main():
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        ctx = await b.new_context(locale="en-US", viewport={"width": 1300, "height": 1000}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        for city, ap in ROUTES:
            pg = await ctx.new_page()
            url = f"https://flights2.flydubai.com/en/results/rt/a1/DXB_{ap}/{OUT_D}_{BACK_D}"
            r = {"city": city, "airport": ap, "url": url}
            try:
                await pg.goto(url, wait_until="domcontentloaded", timeout=90000)
                t = ""
                for i in range(15):
                    await pg.wait_for_timeout(2000)
                    t = await pg.inner_text("body")
                    if "06 November" in t and "01 November" in t: break
                r["out"] = day_price(t, "01 November"); r["back"] = day_price(t, "06 November")
                await pg.screenshot(path=f"fz_{ap}.png")
                if "no flights" in t.lower() or "not available" in t.lower(): r["note"] = "no flights message"
            except Exception as e:
                r["error"] = f"{type(e).__name__}: {e}"[:150]
            res[ap] = r; print(city, ap, r.get("out"), r.get("back"), r.get("error", ""), flush=True)
            json.dump(res, open(RES, "w"), ensure_ascii=False, indent=1)
            await pg.close(); await asyncio.sleep(3)
        await b.close()
asyncio.run(main())
