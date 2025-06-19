#!/usr/bin/env python3
"""
Test Playwright on Windows with proper event loop policy.
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_playwright_windows():
    """Test Playwright with Windows-specific fixes."""
    print("🔍 Testing Playwright on Windows...")
    
    try:
        # Set Windows event loop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("✅ Set Windows ProactorEventLoopPolicy")
        
        print("1. Starting Playwright...")
        playwright = await async_playwright().start()
        print("✅ Playwright started successfully")
        
        print("2. Launching browser...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        print("✅ Browser launched successfully")
        
        print("3. Creating context...")
        context = await browser.new_context()
        print("✅ Context created successfully")
        
        print("4. Creating page...")
        page = await context.new_page()
        print("✅ Page created successfully")
        
        print("5. Testing navigation...")
        await page.goto("https://httpbin.org/html", timeout=10000)
        title = await page.title()
        print(f"✅ Navigation successful - Title: {title}")
        
        # Cleanup
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        print("\n🎉 Windows Playwright test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set event loop policy before running
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    success = asyncio.run(test_playwright_windows())
    if success:
        print("\n✅ RESULT: Playwright works on Windows!")
    else:
        print("\n❌ RESULT: Playwright has issues on Windows")
