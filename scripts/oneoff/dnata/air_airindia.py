"""Air India (airindia.com), return search DXB-DEL, 1 adult, economy: fill the home-page booking widget and
dump the results page text + any JSON responses for parsing.
STATUS: NOT WORKING from the cloud runner. www.airindia.com (Akamai) serves the home page once to a fresh
browser profile, then answers "Access Denied" to every request from the same IP (also with new profiles).
The form steps below were verified up to the date picker; the search/results step was never reached.
Run from a normal UAE desktop/office connection.
usage: xvfb-run -a python3 air_airindia.py"""
import asyncio, tempfile
from patchright.async_api import async_playwright
EXE = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="ai_"), headless=False, executable_path=EXE,
                                                         no_viewport=True, locale="en-US")
        pg = ctx.pages[0]; dumps = []
        async def on(r):
            if r.request.resource_type in ("xhr", "fetch") and "json" in (r.headers.get("content-type") or ""):
                try: dumps.append((r.url, await r.text()))
                except Exception: pass
        pg.on("response", on)
        await pg.goto("https://www.airindia.com/", wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(10000)
        if "Access Denied" in await pg.inner_text("body"): raise SystemExit("Akamai: Access Denied")
        try: await pg.click("#onetrust-accept-btn-handler", timeout=4000)
        except Exception: pass
        ins = pg.locator('input[aria-label="Select origin airport"]')
        await ins.nth(0).click(); await pg.keyboard.press("Control+A"); await pg.keyboard.type("Dubai", delay=120); await pg.wait_for_timeout(2500)
        await pg.locator('[role=option]:has-text("DXB")').first.click(); await pg.wait_for_timeout(1500)
        await ins.nth(1).click(); await pg.keyboard.type("Delhi", delay=120); await pg.wait_for_timeout(2500)
        await pg.locator('[role=option]:has-text("DEL")').first.click(); await pg.wait_for_timeout(1500)
        await pg.click('button[aria-label="Open date picker"]'); await pg.wait_for_timeout(2500)
        # Nov 2026 calendar: pick 1 Nov then 6 Nov (cells show round-trip fare under the day number)
        for day in ("1", "6"):
            await pg.locator("text=November 2026").locator("xpath=following::*[normalize-space(text())='%s']" % day).first.click()
            await pg.wait_for_timeout(1200)
        await pg.get_by_role("button", name="Confirm").click(); await pg.wait_for_timeout(1500)
        await pg.get_by_role("button", name="Search").click()
        await pg.wait_for_timeout(40000)
        open("airindia_results.txt", "w").write(await pg.inner_text("body"))
        for i, (u, b) in enumerate(dumps): open(f"airindia_resp_{i}.json", "w").write(b)
        await pg.screenshot(path="airindia_results.png", full_page=True)
        await ctx.close()
asyncio.run(main())
