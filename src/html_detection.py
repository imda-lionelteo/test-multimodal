import argparse
import json
import re
from pathlib import Path

from PIL import Image

VIEWPORT = {"width": 1440, "height": 900}


def slugify(text: str, limit: int = 40) -> str:
    """Turn link text into a filename-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:limit] or "link"


def load(page, html_path: Path):
    """Load a local HTML file fresh and let fonts/JS settle."""
    page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
    page.wait_for_timeout(1500)


def capture_html(page, html_path: Path, out_dir: Path):
    """Screenshot the page on load, then one screenshot per link after clicking it."""
    from playwright.sync_api import Error as PlaywrightError

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    load(page, html_path)
    page.screenshot(path=out_dir / "00_full_page.png", full_page=True)
    page.screenshot(path=out_dir / "00_initial_view.png")
    manifest.append({"file": "00_full_page.png", "href": None, "text": "full page on load"})
    manifest.append({"file": "00_initial_view.png", "href": None, "text": "viewport on load"})

    link_count = page.locator("a[href]").count()
    for i in range(link_count):
        # Reload so each link is captured from a clean state
        load(page, html_path)
        link = page.locator("a[href]").nth(i)
        href = link.get_attribute("href") or ""
        text = (link.text_content() or link.get_attribute("aria-label") or "").strip()
        text = " ".join(text.split())
        filename = f"{i + 1:02d}_{slugify(text or href)}.png"

        # Keep mailto:, tel: and external links from leaving the page
        if not href.startswith("#"):
            link.evaluate("el => el.addEventListener('click', e => e.preventDefault())")

        try:
            link.scroll_into_view_if_needed(timeout=2000)
            link.click(timeout=3000)
            method = "click"
        except PlaywrightError:
            # Hidden or covered (e.g. behind a modal) - fire the click directly
            link.evaluate("el => el.click()")
            method = "js-click"

        page.wait_for_timeout(1000)
        page.screenshot(path=out_dir / filename)
        manifest.append({"file": filename, "href": href, "text": text, "method": method})
        print(f"  [{i + 1}/{link_count}] {href:<30} {text[:40]!r} -> {filename} ({method})")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def capture_all(input_dir: Path, shots_root: Path):
    # Imported here so the detect step doesn't need playwright installed
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport=VIEWPORT)
        for html_path in sorted(input_dir.glob("*.html")):
            print(f"Capturing {html_path.name}")
            capture_html(page, html_path, shots_root / html_path.stem)
        browser.close()


def detect_all(shots_root: Path, masks_root: Path, target: Path | None = None):
    # Imported here so the capture step doesn't need a Gemini API key
    from image_detection import extract_segmentation_masks, plot_segmentation_masks

    # Narrow to a single folder or image inside shots_root if requested
    if target is None:
        pngs = sorted(shots_root.rglob("*.png"))
    elif target.is_file():
        pngs = [target]
    else:
        pngs = sorted(target.rglob("*.png"))

    for png in pngs:
        rel = png.resolve().relative_to(shots_root.resolve())
        dst = masks_root / rel.parent / f"masks_{rel.name}"
        if dst.exists():
            print(f"{rel}: skipped, already exists at {dst} (delete it to re-run)")
            continue  # already processed - lets you resume after a failure
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            im = Image.open(png).convert("RGB")
            segmentation_masks = extract_segmentation_masks(im)
            plot_segmentation_masks(im, segmentation_masks).save(dst)
            print(f"{rel}: {len(segmentation_masks)} detections -> {dst}")
        except Exception as e:
            print(f"{rel}: FAILED ({e})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Screenshot every link state of HTML pages and run dark-pattern detection.")
    parser.add_argument("--input", default="reference/claude_sonnet4.6")
    parser.add_argument("--output", default="output/claude_sonnet4.6")
    parser.add_argument("--skip-capture", action="store_true")
    parser.add_argument("--skip-detect", action="store_true")
    parser.add_argument("--target", help="Only detect on this screenshot folder or image (implies --skip-capture)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    target = Path(args.target) if args.target else None
    if not args.skip_capture and target is None:
        capture_all(Path(args.input), output_dir / "screenshots")
    if not args.skip_detect:
        detect_all(output_dir / "screenshots", output_dir / "masks", target)
