import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width':1440,'height':900}, color_scheme='light', geolocation={'latitude':45.6427,'longitude':25.5887}, permissions=['geolocation'])
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
        pg.on('console', lambda m: print('CONSOLE', m.text[:200]) if m.type in ('error','warning') and 'GL' not in m.text and 'swiftshader' not in m.text.lower() and 'globe' not in m.text and 'TUNNEL' not in m.text else None)
        await pg.goto('http://localhost:8765/index.html#map=10.8/45.6/25.58'); await pg.wait_for_timeout(14000)
        await pg.screenshot(path='/tmp/a0.png')
        # timing of ranking
        ms = await pg.evaluate("(()=>{const t=performance.now(); window.__rk=''; document.querySelector('#lsSort').dispatchEvent(new Event('change')); return performance.now()-t;})()")
        print('renderLs ms', round(ms,1))
        print('sub', await pg.evaluate("document.querySelector('#lsSub').textContent"), '|', await pg.evaluate("document.querySelector('#exTitle').textContent"))
        print('rows', await pg.evaluate("[...document.querySelectorAll('#lsList .sp-row')].slice(0,6).map(r=>r.querySelector('b').textContent+' / '+r.querySelector('.pct').textContent+' / '+(r.querySelector('.tr')||{}).textContent)"))
        await pg.select_option('#lsSort','edibility'); await pg.wait_for_timeout(300); await pg.screenshot(path='/tmp/a1.png')
        await pg.select_option('#lsSort','forecast')
        await pg.click('#dchip'); await pg.click('[data-d="7"]'); await pg.wait_for_timeout(1500); await pg.keyboard.press('Escape'); await pg.screenshot(path='/tmp/a2.png')
        print('hash', await pg.evaluate("location.hash"))
        await pg.click('#home'); await pg.wait_for_timeout(3500); await pg.screenshot(path='/tmp/a3.png')
        await pg.click('#lsList .sp-row:nth-child(3)'); await pg.wait_for_timeout(1500); await pg.screenshot(path='/tmp/a4.png')
        print('hash2', await pg.evaluate("location.hash"))
        # reload with hash state
        await pg.goto('http://localhost:8765/index.html#map=10.8/45.6/25.58&sp=Cantharellus%20cibarius&d=3&v=habitat'); await pg.wait_for_timeout(12000); await pg.screenshot(path='/tmp/a5.png')
        print('state', await pg.evaluate("[document.querySelector('#lgSp').textContent, document.querySelector('#dchipT').textContent, [...document.querySelectorAll('#mseg [aria-pressed=true]')].map(b=>b.textContent)]"))
        await ctx.close(); await b.close()
asyncio.run(main())
