"""Real Chromium UI checks with page JavaScript disabled. Run after app.py."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/screenshots"
BASE = "http://127.0.0.1:5067"
PAGES = [("overview", "/"), ("mission", "/mission"),
         ("vaccination", "/vaccinations?antigen=RCV1&year=2000"),
         ("infections", "/infections?economy=4&infection=MEA&year=2022"),
         ("improvement", "/improvements?antigen=DTPCV1&start=2000&end=2024"),
         ("benchmark", "/benchmark?infection=MEA&year=2020")]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for width, height in [(1440, 1000), (390, 844), (320, 740)]:
            context = browser.new_context(viewport={"width": width, "height": height},
                                          java_script_enabled=False)
            page = context.new_page()
            failures = []
            page.on("requestfailed", lambda req: failures.append(req.url))
            for name, path in PAGES:
                started = time.perf_counter()
                response = page.goto(BASE + path, wait_until="networkidle")
                assert response.status == 200, (path, response.status)
                assert page.locator("h1").count() == 1
                assert page.locator("script").count() == 0
                assert page.locator("nav a").count() == 6
                # Tables may scroll inside labelled containers; page-level controls must fit.
                for locator in page.locator("h1,h2,.brand,.fact-card strong,.field input,.field select,.navigation a,.table-scroll,meter").all():
                    box = locator.bounding_box()
                    if box:
                        assert box["x"] >= -1 and box["x"] + box["width"] <= width + 1, (name, width, box)
                controls = [x.bounding_box() for x in page.locator(".field").all()]
                for i, a in enumerate(controls):
                    for b in controls[i+1:]:
                        if a and b:
                            overlap_x = min(a["x"]+a["width"], b["x"]+b["width"])-max(a["x"], b["x"])
                            overlap_y = min(a["y"]+a["height"], b["y"]+b["height"])-max(a["y"], b["y"])
                            assert overlap_x <= 1 or overlap_y <= 1, (name, width, "overlapping fields")
                page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
                report.append({"page": name, "width": width, "status": response.status,
                               "seconds_including_capture": round(time.perf_counter()-started, 3)})
                print(f"PASS {name} {width}px", flush=True)
            # Exercise real form submission, persisted selection and sort.
            page.goto(BASE + "/vaccinations")
            page.locator("#antigen").select_option("RCV1")
            page.locator("#year").select_option("2000")
            page.locator("#minimum").fill("90")
            page.get_by_role("button", name="Apply filters").click()
            table = page.get_by_role("region", name="Country coverage results")
            assert table.locator("tbody tr").count() == 2
            assert "Singapore" in table.inner_text() and "Malta" in table.inner_text()
            assert page.locator("#antigen").input_value() == "RCV1"
            page.locator("#sort").select_option("coverage")
            page.locator("#direction").select_option("desc")
            page.get_by_role("button", name="Apply filters").click()
            assert table.locator("tbody tr").first.locator("th").inner_text() == "Singapore"
            page.locator("#minimum").fill("99")
            page.get_by_role("button", name="Apply filters").click()
            assert page.get_by_text("No matching results", exact=True).is_visible()
            page.get_by_role("link", name="Reset filters", exact=True).click()
            assert page.locator("#minimum").input_value() == "90"
            page.get_by_role("link", name="Improvement", exact=True).click()
            page.locator("#start").select_option("2024")
            page.locator("#end").select_option("2000")
            page.get_by_role("button", name="Apply filters").click()
            assert page.get_by_role("alert").is_visible()
            assert not failures, failures
            context.close()
        browser.close()
    (ROOT / "docs/browser-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print("18 screenshots, all six pages at three widths; form workflows passed.")


if __name__ == "__main__":
    main()
