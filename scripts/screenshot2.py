#!/usr/bin/env python3
import asyncio
import http.server
import threading
from playwright.async_api import async_playwright

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='~/.openclaw/workspace', **kwargs)

async def main():
    server = http.server.HTTPServer(('127.0.0.1', 9877), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            # 1.5x layout, but device_scale_factor=2 → outputs 2x pixel density
            page = await browser.new_page(
                viewport={'width': 1800, 'height': 1350},
                device_scale_factor=2
            )
            await page.goto('http://127.0.0.1:9877/four-disciplines.html',
                            wait_until='load', timeout=30000)
            await asyncio.sleep(2)
            await page.screenshot(path='~/.openclaw/workspace/four-disciplines.png',
                                  full_page=True)
            await browser.close()
            print("Screenshot saved: 1.5x layout + 2x DPI = 3600x2700 output!")
    finally:
        server.shutdown()

asyncio.run(main())
