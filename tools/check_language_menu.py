"""Exercise the native language menu with JavaScript disabled."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    for width in (1440, 390, 320):
        context = browser.new_context(viewport={"width": width, "height": 900},
                                      java_script_enabled=False)
        page = context.new_page()
        page.goto("http://127.0.0.1:5067/vaccinations?antigen=RCV1&year=2000")
        for code in ("vi", "es", "fr", "de", "zh", "en"):
            page.locator(".globe-trigger").click()
            menu = page.locator(".language-menu")
            assert menu.is_visible()
            box = menu.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= width
            assert menu.locator("a").count() == 6
            assert page.locator(".language-picker button").count() == 0
            link = menu.locator('a[href*="language=' + code + '"]')
            link.hover()
            link.click()
            page.wait_for_load_state("networkidle")
            assert "antigen=RCV1" in page.url and "year=2000" in page.url
            assert page.locator("html").get_attribute("lang") == ("zh-Hans" if code == "zh" else code)
            assert "Singapore" in page.locator("body").inner_text()
            assert page.locator("script").count() == 0
        page.locator(".globe-trigger").focus()
        page.keyboard.press("Enter")
        assert page.locator(".language-menu").is_visible()
        page.screenshot(path=str(ROOT / "docs/screenshots" / f"sage-menu-{width}.png"))
        assert page.evaluate("document.fonts.check('16px Roboto')")
        print(f"PASS language links, filters, keyboard and Roboto: {width}px")
        context.close()
    browser.close()
