#!/usr/bin/env python3
"""Pages acceptance proof for market-brief v2 PREVIEW (Chromium + WebKit)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "index.html"
SHOTS = ROOT / "proof" / "shots"
OUT = ROOT / "proof" / "summary.json"

VIEWPORTS = [
    ("320x568", 320, 568),
    ("320x720", 320, 720),
    ("360x800", 360, 800),
    ("390x844", 390, 844),
    ("430x932", 430, 932),
    ("667x390", 667, 390),
    ("1280x800", 1280, 800),
]

OVERFLOW_WIDTHS = [320, 360, 390, 430, 667, 1280]

TAP_SELECTOR = (
    ".skip-link, .toc a, .back-top, details summary"
)

OVERFLOW_JS = """
(width) => {
  const sel = [
    'html', 'body',
    '.masthead-wrap',
    '#snapshot',
    '#name-liauto-1, .stock',
    '#sources'
  ];
  const results = [];
  for (const s of sel) {
    const el = document.querySelector(s);
    if (!el) {
      results.push({ selector: s, missing: true });
      continue;
    }
    const sw = el.scrollWidth;
    const cw = el.clientWidth;
    results.push({
      selector: s,
      scrollWidth: sw,
      clientWidth: cw,
      overflow: sw - cw,
    });
  }
  return { width, results };
}
"""

FIRST_SCREEN_JS = """
() => {
  const snap = document.querySelector('#snapshot');
  const mast = document.querySelector('.masthead-wrap');
  const table = document.querySelector('.snapshot-table');
  const vh = window.innerHeight;
  const vis = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const top = r.top;
    const bottom = r.bottom;
    const visiblePx = Math.max(0, Math.min(bottom, vh) - Math.max(top, 0));
  const height = r.height;
    return {
      top, bottom, height,
      visiblePx,
      startsInView: top < vh,
      fullyInView: top >= 0 && bottom <= vh,
      fraction: height > 0 ? visiblePx / height : 0,
    };
  };
  const rows = [...document.querySelectorAll('.snapshot-table tbody tr')].map((tr, i) => {
    const r = tr.getBoundingClientRect();
    const visiblePx = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    return {
      i,
      name: tr.querySelector('.index-name, th')?.innerText?.trim().split('\\n')[0] || '',
      top: r.top, bottom: r.bottom, height: r.height,
      visiblePx,
      startsInView: r.top < vh,
      fullyInView: r.top >= 0 && r.bottom <= vh,
      fraction: r.height > 0 ? visiblePx / r.height : 0,
    };
  });
  return {
    viewportH: vh,
    masthead: vis(mast),
    snapshot: vis(snap),
    table: vis(table),
    rows,
  };
}
"""


def measure_taps(page) -> dict:
    below = []
    items = page.locator(TAP_SELECTOR).all()
    for el in items:
        box = el.bounding_box()
        if not box:
            continue
        h = max(box["height"], box["width"])
        text = el.inner_text()[:80].replace("\n", " ")
        if h < 44:
            below.append({"text": text, "size": round(h, 1)})
    return {"count": len(items), "below44": below}


def run_engine(browser_type: str, p) -> dict:
    browser = p[browser_type].launch()
    overflow_report = []
    tap_report = []
    first_screen = []
    webkit_note = None

    for vp_name, w, h in VIEWPORTS:
        ctx = browser.new_context(
            viewport={"width": w, "height": h},
            device_scale_factor=1,
        )
        page = ctx.new_page()
        page.goto(HTML.as_uri())
        page.wait_for_load_state("networkidle")

        if w in OVERFLOW_WIDTHS and h in (568, 720, 800, 844, 932, 390, 800):
            # use standard height 800 for overflow-only widths except listed viewports
            pass
        if vp_name in ("320x568", "390x844", "1280x800", "667x390"):
            shot = SHOTS / browser_type / f"first-{vp_name}.png"
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=False)

        if vp_name == "390x844":
            for label, action in [
                ("how-to-read-closed", None),
                ("how-to-read-open", lambda: page.locator("#how-to-read details.method-details").first.click()),
                ("name-liauto", lambda: page.locator("#name-2015-hk-1").scroll_into_view_if_needed()),
                ("sources", lambda: page.locator("#sources").scroll_into_view_if_needed()),
            ]:
                if action:
                    action()
                    page.wait_for_timeout(200)
                page.screenshot(
                    path=str(SHOTS / browser_type / f"{label}-390x844.png"),
                    full_page=False,
                )
                if label == "how-to-read-open":
                    page.locator("#how-to-read details.method-details").first.click()

        fs = page.evaluate(FIRST_SCREEN_JS)
        fs["viewport"] = vp_name
        first_screen.append(fs)

        if w in OVERFLOW_WIDTHS:
            page.set_viewport_size({"width": w, "height": h})
            data = page.evaluate(OVERFLOW_JS, w)
            overflow_report.append({"viewport": f"{w}px", **data})

        tap_report.append({"page": vp_name, **measure_taps(page)})
        ctx.close()

    browser.close()
    fails = sum(
        1
        for block in overflow_report
        for r in block["results"]
        if not r.get("missing") and r.get("overflow", 0) != 0
    )
    tap_fails = sum(len(t["below44"]) for t in tap_report)
    return {
        "engine": browser_type,
        "overflowFails": fails,
        "tapBelow44Count": tap_fails,
        "overflow": overflow_report,
        "tapTargets": tap_report,
        "firstScreen": first_screen,
        "webkitNote": webkit_note,
        "pass": fails == 0 and tap_fails == 0,
    }


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    scanned = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    results = {"scannedAt": scanned, "html": str(HTML), "engines": {}}

    with sync_playwright() as p:
        results["engines"]["chromium"] = run_engine("chromium", p)
        try:
            results["engines"]["webkit"] = run_engine("webkit", p)
            results["webkitStatus"] = "OK"
        except Exception as exc:  # noqa: BLE001
            results["engines"]["webkit"] = {"error": str(exc), "pass": False}
            results["webkitStatus"] = f"PARTIAL: {exc}"

    ch = results["engines"]["chromium"]
    results["summary"] = {
        "chromiumPass": ch.get("pass"),
        "webkitPass": results["engines"].get("webkit", {}).get("pass"),
        "webkitStatus": results.get("webkitStatus"),
        "overflowFails": ch.get("overflowFails", 0),
        "tapBelow44": ch.get("tapBelow44Count", 0),
    }
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()