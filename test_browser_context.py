#!/usr/bin/env python3
"""
Quick test to diagnose browser context acquisition issue.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_basic_playwright():
    """Test basic Playwright functionality."""
    print("🔍 Testing basic Playwright functionality...")
    
    try:
        # Test 1: Basic Playwright startup
        print("1. Starting Playwright...")
        playwright = await async_playwright().start()
        print("✅ Playwright started successfully")
        
        # Test 2: Browser launch
        print("2. Launching browser...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        print("✅ Browser launched successfully")
        
        # Test 3: Context creation
        print("3. Creating browser context...")
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        print("✅ Browser context created successfully")
        
        # Test 4: Page creation
        print("4. Creating page...")
        page = await context.new_page()
        print("✅ Page created successfully")
        
        # Test 5: Simple navigation
        print("5. Testing navigation...")
        await page.goto("https://httpbin.org/html", timeout=10000)
        title = await page.title()
        print(f"✅ Navigation successful - Page title: {title}")
        
        # Cleanup
        print("6. Cleaning up...")
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        print("✅ Cleanup completed")
        
        print("\n🎉 All browser tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Browser test failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

async def test_browser_pool():
    """Test our browser pool manager."""
    print("\n🔍 Testing Browser Pool Manager...")
    
    try:
        from app.utils.browser_pool import browser_pool
        
        print("1. Initializing browser pool...")
        await browser_pool.initialize()
        print("✅ Browser pool initialized")
        
        print("2. Acquiring context...")
        context = await browser_pool.acquire_context(task_id=999)
        print("✅ Context acquired")
        
        print("3. Creating page...")
        page = await context.new_page()
        print("✅ Page created")
        
        print("4. Testing navigation...")
        await page.goto("https://httpbin.org/html", timeout=10000)
        title = await page.title()
        print(f"✅ Navigation successful - Page title: {title}")
        
        print("5. Releasing context...")
        await page.close()
        await browser_pool.release_context(task_id=999, context=context)
        print("✅ Context released")
        
        print("6. Getting pool stats...")
        stats = await browser_pool.get_pool_stats()
        print(f"✅ Pool stats: {stats}")
        
        print("\n🎉 Browser pool tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Browser pool test failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 BROWSER CONTEXT DIAGNOSTIC TEST")
    print("=" * 50)
    
    # Test basic Playwright
    basic_success = await test_basic_playwright()
    
    if basic_success:
        # Test our browser pool
        pool_success = await test_browser_pool()
        
        if pool_success:
            print("\n✅ DIAGNOSIS: Browser context system is working!")
        else:
            print("\n⚠️ DIAGNOSIS: Issue is in our browser pool configuration")
    else:
        print("\n❌ DIAGNOSIS: Issue is with basic Playwright setup")
        print("💡 SOLUTION: Run 'python -m playwright install chromium'")

if __name__ == "__main__":
    asyncio.run(main())
