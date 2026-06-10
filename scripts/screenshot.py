#!/usr/bin/env python3
import asyncio
import http.server
import threading
from playwright.async_api import async_playwright

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='~/.openclaw/workspace', **kwargs)

async def main():
    server = http.server.HTTPServer(('127.0.0.1', 9876), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page(viewport={'width': 1800, 'height': 1350})
            await page.goto('http://127.0.0.1:9876/memory_framework.html',
                            wait_until='networkidle', timeout=60000)
            await asyncio.sleep(2)
            await page.screenshot(path='~/.openclaw/workspace/memory_framework.png',
                                  full_page=True)
            await browser.close()
            print("Screenshot saved at 1.5x resolution (1800x1350)!")
    finally:
        server.shutdown()

asyncio.run(main())
