"""Turkish Airlines (turkishairlines.com) probe: DXB-IST 1 Nov / IST-DXB 6 Nov 2026.
Result 22 Oct 2026: blocked. The home page loads (200), but a PerimeterX "Press & Hold" human check
(iframe #px-captcha-modal) covers the search form before anything can be typed, so no search runs.
Not bypassed on purpose (solving the human check is out of scope).
usage: xvfb-run -a python3 air_turkish.py"""
import asyncio, json
from patchright.async_api import async_playwright
EXE = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/tkprof", headless=False, executable_path=EXE, no_viewport=True, locale="en-US")
        pg = ctx.pages[0]
        r = await pg.goto("https://www.turkishairlines.com/en-ae/", wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(8000)
        px = await pg.evaluate("()=>!!document.querySelector('#px-captcha-modal')")
        res = {"IST": {"status": "blocked" if px else "form reachable", "home_http": r.status if r else None,
                       "detail": "PerimeterX Press & Hold human check (#px-captcha-modal) covers the search form" if px else ""}}
        json.dump(res, open("air_turkish_res.json", "w"), indent=1); print(res)
        await ctx.close()
asyncio.run(main())
