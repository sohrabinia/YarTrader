import asyncio
from playwright.async_api import async_playwright
import os

routes = [
    ("#/", "01_landing.png"),
    ("#/features", "02_features.png"),
    ("#/pricing", "03_pricing.png"),
    ("#/blog", "04_blog.png"),
    ("#/login", "05_login.png"),
    ("#/register", "06_register.png"),
    ("#/forgot-password", "07_forgot_password.png"),
    ("#/dashboard", "08_terminal_dashboard.png"),
    ("#/backtest", "09_backtest.png"),
    ("#/demo", "10_demo.png"),
    ("#/shadow", "11_shadow.png"),
    ("#/live", "12_live_gate.png"),
    ("#/signals", "13_signals.png"),
    ("#/execution-intel", "14_execution_intel.png"),
    ("#/learning", "15_learning.png"),
    ("#/admin", "16_admin.png"),
]

async def capture_v5_all():
    out_dir = "validation/frontend_v5_implementation"
    os.makedirs(out_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # Inject auth token into localStorage
        await page.goto("http://localhost:3000/#/login", timeout=10000)
        await page.evaluate("""() => {
            localStorage.setItem('yartrader_token', 'v5_implementation_verified_token');
            localStorage.setItem('yartrader_role', 'ADMIN');
            localStorage.setItem('yartrader_name', 'SRE Lead Developer');
            localStorage.setItem('yartrader_language', 'fa');
        }""")

        # Capture Desktop 16 routes
        for hash_route, filename in routes:
            url = f"http://localhost:3000/{hash_route}"
            await page.goto(url, timeout=10000)
            await page.wait_for_timeout(300)
            target_path = os.path.join(out_dir, filename)
            await page.screenshot(path=target_path, full_page=False)
            print(f"Captured V5: {target_path}")

        # Capture Persian RTL Desktop
        await page.goto("http://localhost:3000/#/dashboard", timeout=10000)
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(out_dir, "17_fa_rtl_desktop.png"), full_page=False)
        print("Captured V5: 17_fa_rtl_desktop.png")

        # Capture Arabic RTL Desktop
        await page.evaluate("() => localStorage.setItem('yartrader_language', 'ar')")
        await page.reload(timeout=10000)
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(out_dir, "18_ar_rtl_desktop.png"), full_page=False)
        print("Captured V5: 18_ar_rtl_desktop.png")

        # Capture Mobile Viewport 375px
        mobile_page = await browser.new_page(viewport={"width": 375, "height": 812})
        await mobile_page.goto("http://localhost:3000/#/dashboard", timeout=10000)
        await mobile_page.evaluate("""() => {
            localStorage.setItem('yartrader_token', 'v5_implementation_verified_token');
            localStorage.setItem('yartrader_role', 'ADMIN');
            localStorage.setItem('yartrader_name', 'SRE Mobile Developer');
            localStorage.setItem('yartrader_language', 'fa');
        }""")
        await mobile_page.reload(timeout=10000)
        await mobile_page.wait_for_timeout(300)
        await mobile_page.screenshot(path=os.path.join(out_dir, "19_mobile_375px_dashboard.png"), full_page=False)
        print("Captured V5: 19_mobile_375px_dashboard.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_v5_all())
