import asyncio, sys
from playwright.async_api import async_playwright
V=[('d_light',1440,900,'light',False,'#map=10.8/45.6/25.58'),('d_dark',1440,900,'dark',False,'#map=10.8/45.6/25.58'),('tab',1024,768,'light',False,'#map=10/45.6/25.58'),('ph',390,844,'light',True,'#map=10.5/45.6/25.58')]
only = sys.argv[1:] 
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
        for name,w,h,sc,mob,hs in V:
            if only and name not in only: continue
            pg = await b.new_page(viewport={'width':w,'height':h}, color_scheme=sc, is_mobile=mob, has_touch=mob)
            pg.on('pageerror', lambda e: print('PAGEERROR', str(e)[:500]))
            pg.on('console', lambda m: print('CONSOLE', m.text[:200]) if m.type in ('error','warning') and 'GL' not in m.text and 'swiftshader' not in m.text.lower() and 'globe' not in m.text and 'TUNNEL' not in m.text else None)
            await pg.goto('http://localhost:8765/index.html'+hs); await pg.wait_for_timeout(15000)
            await pg.screenshot(path=f'/tmp/u_{name}.png')
            await pg.close()
        await b.close()
asyncio.run(main())
