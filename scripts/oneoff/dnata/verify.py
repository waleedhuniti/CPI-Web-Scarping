"""Check one package page: is a cheaper room of the same board offered, and which Emirates direct fares exist."""
import asyncio, json, re, sys, os
from playwright.async_api import async_playwright
CI, CO = os.environ["CHECKIN"], os.environ["CHECKOUT"]
res = json.load(open(sys.argv[1]))
async def wait_text(pg, needle, n=20):
    for i in range(n):
        await pg.wait_for_timeout(2000)
        if needle in await pg.inner_text('body'): return True
    return False
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        ctx = await b.new_context(locale="en-US", viewport={"width": 1300, "height": 1000}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        for k, v in res.items():
            pg = await ctx.new_page()
            did = re.search(r'\((\d+)\)', v['destination']).group(1)
            board = "&hotelFilters.boardTypes=2" if v.get('board_rule') == 'Bed & Breakfast' else ""
            await pg.goto(f"https://www.dnatatravel.com/holidays/hotels?checkIn={CI}&checkOut={CO}&destIds={did}&tripType=HOLIDAY&rooms.0.adults=1&depAirports=DXB&adults=1&cabin=1&dateSearchType=CHOOSE_DATE&priceDisplayMode=2&sort=PRICE_LOWEST_FIRST{board}", wait_until='domcontentloaded', timeout=90000)
            await wait_text(pg, 'Total AED')
            q = pg.url.split('?', 1)[1]
            await pg.goto(f"https://www.dnatatravel.com/holidays/hotels/{v['estab_id']}?{q}", wait_until='domcontentloaded', timeout=90000)
            await wait_text(pg, 'Total holiday')
            await pg.evaluate("document.querySelectorAll('#onetrust-consent-sdk').forEach(e=>e.remove())")
            body = await pg.inner_text('body')
            i0 = body.find('Select board type and room'); rooms = body[i0:i0 + 3000]
            sel_board = re.search(r'\n([^\n]+)\n\nSelected', rooms)
            cheaper_rooms = re.findall(r'-\s*AED\s*([\d,]+)\s*total', rooms.split('Selected', 2)[-1])
            await pg.get_by_role('button', name='Change flight').first.click(); await pg.wait_for_timeout(6000)
            dlg = pg.locator('[role=dialog]').first
            await dlg.locator('label', has_text='Direct').first.click(); await pg.wait_for_timeout(4000)
            ek = dlg.locator('label', has_text=re.compile(r'^\s*Emirates\s*$'))
            if await ek.count() == 0 or not await ek.first.is_visible():
                for bb in await dlg.get_by_role('button', name=re.compile(r'^Show \d+ more$')).all(): await bb.click(); await pg.wait_for_timeout(800)
            await ek.first.click(); await pg.wait_for_timeout(5000)
            t = await dlg.inner_text()
            fares = [float(x.replace(',', '')) for x in re.findall(r'\+\s*AED\s*([\d,]+)\s*\n\s*Includes', t)] or [float(x.replace(',', '')) for x in re.findall(r'AED\s*([\d,]+)\s*\n\+', t)]
            print(k, v['hotel_found'], '| board selected:', sel_board.group(1) if sel_board else '?', '| cheaper rooms same board:', cheaper_rooms or 'none',
                  '| Emirates direct fares (+AED):', sorted(set(fares))[:6], flush=True)
            await pg.close()
        await b.close()
asyncio.run(main())
