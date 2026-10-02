import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        pg = await b.new_page(viewport={'width':1440,'height':900}, color_scheme='light')
        pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
        await pg.goto('http://localhost:8765/index.html#map=10.8/45.6/25.58&sp=Cantharellus%20cibarius&d=3&v=habitat'); await pg.wait_for_timeout(13000)
        print('state', await pg.evaluate("[document.querySelector('#lgSp').textContent, document.querySelector('#dchipT').textContent, [...document.querySelectorAll('#mseg [aria-pressed=true]')].map(b=>b.textContent), document.querySelector('#lsSub').textContent]"))
        await pg.screenshot(path='/tmp/b0.png')
        await pg.click('#btnLayers'); await pg.click('[data-v="rain"]'); await pg.wait_for_timeout(600); await pg.screenshot(path='/tmp/b1.png')
        print('seg', await pg.evaluate("[...document.querySelectorAll('#mseg button')].map(b=>b.textContent+':'+b.getAttribute('aria-pressed'))"), await pg.evaluate("location.hash"))
        await pg.close()
        pg = await b.new_page(viewport={'width':390,'height':844}, color_scheme='dark', is_mobile=True, has_touch=True)
        pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
        await pg.goto('http://localhost:8765/index.html#map=10.5/45.6/25.58'); await pg.wait_for_timeout(13000)
        await pg.screenshot(path='/tmp/b2.png')
        await pg.tap('#exTitle'); await pg.wait_for_timeout(600); await pg.screenshot(path='/tmp/b3.png')
        # swipe chips horizontally
        await pg.touchscreen.tap(300, 497)
        box = await pg.evaluate("(()=>{const r=document.querySelector('#qchips').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        print('chips box', box, 'snap', await pg.evaluate("document.body.dataset.snap"))
        await pg.tap('#lsList .sp-row:nth-child(2)'); await pg.wait_for_timeout(1500); await pg.screenshot(path='/tmp/b4.png')
        await pg.tap('#detMap'); await pg.wait_for_timeout(600); await pg.screenshot(path='/tmp/b5.png')
        print('snap after cta', await pg.evaluate("document.body.dataset.snap"))
        await b.close()
asyncio.run(main())
