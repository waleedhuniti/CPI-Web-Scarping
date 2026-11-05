"""Screenshot of the final package page (Emirates non-stop selected) for every priced hotel of res file."""
import asyncio, json, re, sys
from playwright.async_api import async_playwright
import os
CI, CO = os.environ.get("CHECKIN", "2026-11-01"), os.environ.get("CHECKOUT", "2026-11-04")
res = json.load(open(sys.argv[1])); OUT = sys.argv[2]
done = json.load(open(OUT)) if len(sys.argv) > 3 else {}
async def wait_text(pg, needle, n=20):
    for i in range(n):
        await pg.wait_for_timeout(2000)
        if needle in await pg.inner_text('body'): return True
    return False
def slug(s): return re.sub(r'[^A-Za-z0-9]+', '_', s or '')[:40]
async def one(ctx, v):
    pg = await ctx.new_page()
    try:
        did = re.search(r'\((\d+)\)', v['destination']).group(1)
        board = "&hotelFilters.boardTypes=2" if v.get('board_rule') == 'Bed & Breakfast' else ""
        url = (f"https://www.dnatatravel.com/holidays/hotels?checkIn={CI}&checkOut={CO}&destIds={did}&tripType=HOLIDAY&rooms.0.adults=1"
               f"&depAirports=DXB&adults=1&cabin=1&dateSearchType=CHOOSE_DATE&priceDisplayMode=2&sort=PRICE_LOWEST_FIRST{board}")
        await pg.goto(url, wait_until='domcontentloaded', timeout=90000)
        await wait_text(pg, 'Total AED')
        q = pg.url.split('?', 1)[1]
        await pg.goto(f"https://www.dnatatravel.com/holidays/hotels/{v['estab_id']}?{q}", wait_until='domcontentloaded', timeout=90000)
        if not await wait_text(pg, 'Total holiday'): return {'error': 'room page did not load'}
        await pg.evaluate("document.querySelectorAll('#onetrust-consent-sdk').forEach(e=>e.remove())")
        # cheapest room of the selected board: a room option shows '-AED n' when it is cheaper than the pre-selected one
        for _ in range(3):
            more = pg.get_by_role('button', name=re.compile(r'^Show \d+ more rooms$'))
            if await more.count(): await more.first.click(); await pg.wait_for_timeout(1500)
        cheaper = []
        for el in await pg.locator('label:has(input[type=radio])').all():
            t = await el.inner_text()
            m = re.search(r'-\s*AED\s*([\d,]+)\s*total', t)
            if m: cheaper.append((float(m.group(1).replace(',', '')), el))
        if cheaper:
            await max(cheaper, key=lambda x: x[0])[1].click(); await pg.wait_for_timeout(5000)
        await pg.get_by_role('button', name='Change flight').first.click()
        await pg.wait_for_timeout(6000)
        dlg = pg.locator('[role=dialog]').first
        await dlg.locator('label', has_text='Direct').first.click(); await pg.wait_for_timeout(4000)
        ek = dlg.locator('label', has_text=re.compile(r'^\s*Emirates\s*$'))
        if await ek.count() == 0 or not await ek.first.is_visible():
            for b in await dlg.get_by_role('button', name=re.compile(r'^Show \d+ more$')).all():
                await b.click(); await pg.wait_for_timeout(1000)
        await ek.first.click(); await pg.wait_for_timeout(5000)
        best = None
        for more in range(4):
            sel = dlg.locator('button', has_text=re.compile(r'^\s*Select\s*$'))
            for i in range(await sel.count()):
                t = await sel.nth(i).locator('xpath=ancestor::*[contains(., "Dubai to")][1]').inner_text()
                if t.count('Direct') < 2 or re.search(r'\d stop', t): continue   # the Emirates filter is ticked: every card listed is Emirates
                m = re.search(r'([+-])\s*AED\s*([\d,]+)', t)
                d = (1 if m.group(1) == '+' else -1) * float(m.group(2).replace(',', '')) if m else 0.0
                if best is None or d < best[0]: best = (d, i)
            if best: break
            mb = dlg.get_by_role('button', name='Show more flights')
            if await mb.count() == 0: break
            await mb.first.click(); await pg.wait_for_timeout(4000)
        if not best: return {'error': 'no Emirates direct flight in the list'}
        sel = dlg.locator('button', has_text=re.compile(r'^\s*Select\s*$'))
        await sel.nth(best[1]).click()
        await pg.wait_for_timeout(3000)
        notice = None
        if 'Important Notice' in await pg.inner_text('body'):
            nights = int(os.environ.get('NIGHTS') or (__import__('datetime').date.fromisoformat(CO) - __import__('datetime').date.fromisoformat(CI)).days)
            opt = pg.locator('label', has_text=f'({nights} nights)').first
            notice = (await pg.locator('text=Important Notice').locator('xpath=ancestor::*[contains(., "Proceed")][1]').inner_text())[:300].replace('\n', ' ')
            if await opt.count(): await opt.click()
            else: await pg.get_by_text(f'({nights} nights)').first.click()
            await pg.wait_for_timeout(800)
            await pg.get_by_role('button', name='Proceed').first.click()
        for i in range(15):
            await pg.wait_for_timeout(2000)
            if await pg.locator('[role=dialog]').count() == 0: break
        await pg.wait_for_timeout(3000)
        body = await pg.inner_text('body')
        m = re.search(r'Total holiday\s*AED\s*([\d,]+)', body)
        nm = re.search(r'(\d+) nights?, 1 adult', body)
        shown = float(m.group(1).replace(',', '')) if m else None
        await pg.get_by_text('Your selected flights').first.scroll_into_view_if_needed()
        await pg.mouse.wheel(0, -260); await pg.wait_for_timeout(800)
        sold_out = None
        if 'the room has sold out' in body:
            # the cheapest room of the board is sold out: take the next room in the list (shown price +AED x), as a buyer would
            radios = pg.locator('input[type=radio]')
            labels = await pg.locator('text=/\\+AED [\\d,]+ total/').all_inner_texts()
            sold_out = labels[:3]
            await pg.locator('text=/\\+AED [\\d,]+ total/').first.click(); await pg.wait_for_timeout(6000)
            body = await pg.inner_text('body')
            m = re.search(r'Total holiday\s*AED\s*([\d,]+)', body); shown = float(m.group(1).replace(',', '')) if m else shown
        nxt_btn = pg.get_by_role('button', name=re.compile(r'^(Next step|Continue to book)$'))
        if await nxt_btn.count() == 0:
            nxt_btn = pg.get_by_text(re.compile(r'^(Next step|Continue to book)$'))
        await nxt_btn.last.click()
        await pg.wait_for_timeout(12000)
        await pg.evaluate("document.querySelectorAll('#onetrust-consent-sdk').forEach(e=>e.remove())")
        nxt = await pg.inner_text('body')
        if 'the room has sold out' in nxt:
            # the cheapest room is sold out after "Continue": pick the next room listed (+AED x total), as a buyer would
            rooms = await pg.locator('text=/\\+AED [\\d,]+ total/').all_inner_texts()
            sold_out = {'next_rooms_listed': rooms[:4]}
            await pg.locator('text=/\\+AED [\\d,]+ total/').first.click(); await pg.wait_for_timeout(6000)
            b2 = await pg.inner_text('body')
            m = re.search(r'Total holiday\s*AED\s*([\d,]+)', b2); sold_out['total_after_room_change'] = m.group(1) if m else None
            await pg.get_by_role('button', name=re.compile(r'^(Next step|Continue to book)$')).last.click()
            await pg.wait_for_timeout(12000)
            await pg.evaluate("document.querySelectorAll('#onetrust-consent-sdk').forEach(e=>e.remove())")
            nxt = await pg.inner_text('body')
        open(f"maldives_next_{v['row']}.txt", 'w').write(pg.url + '\n' + nxt[:6000])
        m2 = re.findall(r'Total[^\n]{0,20}\n?\s*AED\s*([\d,]+)', nxt)
        await pg.screenshot(path=f"cmp/{v['row']:02d}_next_page.png", full_page=False)
        path = f"{os.environ.get('SHOTDIR', 'shots')}/{v['row']:02d}_{slug(v['hotel_found'])}.png"
        await pg.screenshot(path=path)
        return {'sold_out_next_rooms': sold_out, 'next_page_totals': m2, 'next_url': pg.url, 'shown_total': shown, 'flight_delta_shown': best[0], 'screenshot': path, 'page_url': pg.url, 'nights_shown': int(nm.group(1)) if nm else None, 'notice': notice}
    except Exception as e:
        return {'error': f'{type(e).__name__}: {e}'[:200]}
    finally:
        await pg.close()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
        ctx = await b.new_context(locale="en-US", viewport={"width": 1300, "height": 1000},
                                  user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        for k in sorted(res, key=int):
            v = res[k]
            if not v.get('total') or (k in done and done[k].get('shown_total')): continue
            r = await one(ctx, v)
            if r.get('error'):                       # one retry
                r = await one(ctx, v)
            done[k] = r
            json.dump(done, open(OUT, 'w'), ensure_ascii=False, indent=1)
            print(k, v['hotel_found'], 'calc', v['total'], 'shown', r.get('shown_total'), r.get('error', ''), flush=True)
        await b.close()
asyncio.run(main())
