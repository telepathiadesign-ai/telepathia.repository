import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        pg = await b.new_page(viewport={'width':1440,'height':900}, color_scheme='light')
        pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
        pg.on('console', lambda m: print('CONSOLE', m.text[:200]) if m.type in ('error','warning') and 'GL' not in m.text and 'swiftshader' not in m.text.lower() and 'globe' not in m.text and 'TUNNEL' not in m.text else None)
        await pg.goto('http://localhost:8765/index.html#map=10.8/45.6/25.58'); await pg.wait_for_timeout(14000)
        await pg.screenshot(path='/tmp/i0.png')
        await pg.click('#btnLayers'); await pg.wait_for_timeout(800); await pg.screenshot(path='/tmp/i1.png')
        await pg.click('#layersX'); await pg.click('#dchip'); await pg.wait_for_timeout(500); await pg.screenshot(path='/tmp/i2.png')
        await pg.click('#sq'); await pg.keyboard.type('omu'); await pg.wait_for_timeout(500); await pg.screenshot(path='/tmp/i3.png')
        await pg.keyboard.press('Escape'); await pg.fill('#sq',''); await pg.keyboard.type('galbiori'); await pg.wait_for_timeout(300); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000); await pg.screenshot(path='/tmp/i4.png')
        await pg.mouse.click(1000, 600); await pg.wait_for_timeout(2500); await pg.screenshot(path='/tmp/i5.png')
        await pg.click('#cellClose'); await pg.click('#pCollapse'); await pg.wait_for_timeout(2500); await pg.screenshot(path='/tmp/i6.png')
        await pg.click('#btnTheme'); await pg.wait_for_timeout(300); await pg.screenshot(path='/tmp/i7.png'); await pg.click('[data-th="dark"]'); await pg.wait_for_timeout(3000); await pg.screenshot(path='/tmp/i8.png')
        await b.close()
asyncio.run(main())
