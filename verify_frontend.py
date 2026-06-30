from playwright.sync_api import sync_playwright

def run_cuj(page):
    # Wait for the app to load
    page.goto("http://localhost:3000")
    page.wait_for_timeout(2000)

    # Click the Settings button
    page.get_by_role("button", name="ベンチマーク設定").click()
    page.wait_for_timeout(1000)

    # Take a screenshot of the settings panel
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

    # Close button might just be an X with aria-label
    page.get_by_role("button", name="設定を保存して戻る").click()
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    import os
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
