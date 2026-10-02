import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        pg = await b.new_page(viewport={'width':390,'height':844}, color_scheme='light', is_mobile=True, has_touch=True)
        pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
        pg.on('console', lambda m: print('CONSOLE', m.text[:200]) if m.type in ('error','warning') and 'GL' not in m.text and 'swiftshader' not in m.text.lower() and 'globe' not in m.text and 'TUNNEL' not in m.text else None)
        await pg.goto('http://localhost:8765/index.html#map=10.5/45.6/25.58'); await pg.wait_for_timeout(14000)
        await pg.screenshot(path='/tmp/m0.png')
        await pg.tap('#exTitle'); await pg.wait_for_timeout(700); await pg.screenshot(path='/tmp/m1.png')
        await pg.tap('#lsList [data-sp]:nth-child(3)'); await pg.wait_for_timeout(2500); await pg.screenshot(path='/tmp/m2.png')
        await pg.tap('#detBack'); await pg.wait_for_timeout(600); await pg.screenshot(path='/tmp/m3.png')
        await pg.tap('#btnLayers'); await pg.wait_for_timeout(700); await pg.screenshot(path='/tmp/m4.png')
        await pg.touchscreen.tap(200, 90); await pg.wait_for_timeout(300); await pg.tap('#dchip'); await pg.wait_for_timeout(500); await pg.screenshot(path='/tmp/m5.png')
        await pg.tap('#dchip'); await pg.touchscreen.tap(250, 300); await pg.wait_for_timeout(2500); await pg.screenshot(path='/tmp/m6.png')
        await pg.tap('#sq'); await pg.keyboard.type('galbiori'); await pg.wait_for_timeout(400); await pg.screenshot(path='/tmp/m7.png')
        await b.close()
asyncio.run(main())
