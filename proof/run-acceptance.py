#!/usr/bin/env python3
"""Pages acceptance proof for market-brief v4 PREVIEW (Chromium + WebKit)."""
from __future__ import annotations

import json
import re
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

TAP_SELECTOR = ".skip-link, .toc a, .back-top, details summary, .preview-banner-label"

OVERFLOW_JS = """
() => {
  const sel = [
    'html', 'body',
    '.masthead-wrap',
    '#snapshot',
    '#name-ibm-1',
    '#name-ibm-1 .name-chart',
    '#dow-jones .index-charts',
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
  return results;
}
"""

FIRST_SCREEN_JS = """
() => {
  const banner = document.querySelector('.preview-banner');
  const snap = document.querySelector('#snapshot');
  const mast = document.querySelector('.masthead-wrap');
  const table = document.querySelector('.snapshot-table');
  const chartsInHero = document.querySelector('.masthead-wrap .index-charts, .masthead-wrap .name-chart');
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
      name: (tr.querySelector('.index-name, th')?.innerText || '').trim().split('\\n')[0],
      top: r.top, bottom: r.bottom, height: r.height,
      visiblePx,
      startsInView: r.top < vh,
      fullyInView: r.top >= 0 && r.bottom <= vh,
      fraction: r.height > 0 ? visiblePx / r.height : 0,
    };
  });
  return {
    viewportH: vh,
    previewBanner: vis(banner),
    masthead: vis(mast),
    snapshot: vis(snap),
    table: vis(table),
    chartsInHero: !!chartsInHero,
    rows,
  };
}
"""

CONTENT_CHECKS_JS = """
() => {
  const nasdaqPe = document.querySelector('#nasdaq .chart-title');
  const nasdaqPeText = [...document.querySelectorAll('#nasdaq .chart-title')].map(e => e.textContent);
  const hsiPeTitles = [...document.querySelectorAll('#hang-seng .chart-title')].map(e => e.textContent);
  const hsiPeFrame = document.querySelector('#hang-seng .chart-figure:nth-of-type(3) .chart-frame');
  const dowFirst = [...document.querySelectorAll('#snapshot tbody tr')].map((tr) => {
    const raw = (tr.querySelector('.index-name, th')?.textContent || '').trim();
    return raw.split('\\n')[0].replace(/[+−][0-9.,]+%$/, '').trim();
  });
  const hsiPeLabelText = hsiPeFrame
    ? [...hsiPeFrame.querySelectorAll('text')]
        .filter((t) => {
          const y = parseFloat(t.getAttribute('y') || '0');
          return y >= 40 && y <= 280;
        })
        .map((t) => t.textContent)
        .join(' ')
    : '';
  const tmcrSvg = document.querySelector('#name-tmcr-9 .name-chart svg');
  const tmcrText = tmcrSvg ? tmcrSvg.textContent : '';
  return {
    nasdaqChartTitles: nasdaqPeText,
    hasNasdaqPeChart: nasdaqPeText.some(t => /trailing P\\/E/i.test(t)),
    hsiPeTitles,
    hsiPeHas2015: /2015\\.HK/.test(hsiPeLabelText),
    hsiPeHas3690: /3690\\.HK/.test(hsiPeLabelText),
    hsiPeHas1997: /1997\\.HK/.test(hsiPeLabelText),
    tmcrHas200DayMark: /200-day US\\$/i.test(tmcrText),
    previewBannerVisible: !!document.querySelector('.preview-banner'),
    snapshotIndexOrder: dowFirst,
    subtitle: document.querySelector('.masthead-subtitle')?.textContent || '',
    pageTitle: document.title,
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


def _rows(fs_list: list, viewport: str) -> list:
    for fs in fs_list:
        if fs.get("viewport") == viewport:
            return fs.get("rows") or []
    return []


def static_leak_checks() -> dict:
    raw = HTML.read_text(encoding="utf-8")
    patterns = [
        (r"justinksw/market-brief", "repo name"),
        (r"Jessie|Celine|Sua\b", "team name"),
        (r"NOTES-for-team", "team notes"),
        (r"brief-market-brief", "brief file"),
    ]
    leaks = []
    for pat, label in patterns:
        if re.search(pat, raw, re.I):
            leaks.append(label)
    return {
        "htmlLeaks": leaks,
        "usesV4Css": "market-brief-v4.css" in raw,
        "hasPreviewBanner": "preview-banner" in raw,
    }


def run_engine(browser_type: str, p) -> dict:
    browser = p[browser_type].launch()
    overflow_report = []
    tap_report = []
    first_screen = []
    content_checks = None

    for vp_name, w, h in VIEWPORTS:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(HTML.as_uri())
        page.wait_for_load_state("networkidle")

        shot_dir = SHOTS / browser_type
        shot_dir.mkdir(parents=True, exist_ok=True)

        fs = page.evaluate(FIRST_SCREEN_JS)
        fs["viewport"] = vp_name
        first_screen.append(fs)

        page.screenshot(path=str(shot_dir / f"first-{vp_name}.png"), full_page=False)

        if vp_name == "390x844" and browser_type == "chromium":
            page.locator("#how-to-read details.method-details").first.screenshot(
                path=str(shot_dir / "how-to-read-closed-390x844.png")
            )
            page.locator("#how-to-read details.method-details").first.click()
            page.wait_for_timeout(150)
            page.locator("#how-to-read").screenshot(path=str(shot_dir / "how-to-read-open-390x844.png"))
            page.locator("#how-to-read details.method-details").first.click()
            page.locator("#dow-jones .chart-figure").first.scroll_into_view_if_needed()
            page.locator("#dow-jones .chart-figure").first.screenshot(
                path=str(shot_dir / "dow-pct-change-390x844.png")
            )
            page.locator("#name-ibm-1").scroll_into_view_if_needed()
            page.locator("#name-ibm-1").screenshot(
                path=str(shot_dir / "name-ibm-390x844.png")
            )
            page.locator("#name-tmcr-9").scroll_into_view_if_needed()
            page.locator("#name-tmcr-9 .name-chart").screenshot(
                path=str(shot_dir / "chart-tmcr-390x844.png")
            )
            page.locator("#dow-jones .index-charts").screenshot(
                path=str(shot_dir / "dow-comparisons-390x844.png")
            )
            page.locator("#sources").scroll_into_view_if_needed()
            page.screenshot(path=str(shot_dir / "sources-390x844.png"), full_page=False)

        if vp_name == "320x720" and browser_type == "chromium":
            page.locator("#name-ibm-1").scroll_into_view_if_needed()
            page.locator("#name-ibm-1").screenshot(
                path=str(shot_dir / "name-ibm-320x720.png")
            )

        if w in OVERFLOW_WIDTHS and vp_name in (
            "320x568",
            "360x800",
            "390x844",
            "430x932",
            "667x390",
            "1280x800",
        ):
            overflow_report.append(
                {"viewport": f"{w}px", "height": h, "results": page.evaluate(OVERFLOW_JS)}
            )

        tap_report.append({"page": vp_name, **measure_taps(page)})
        if content_checks is None:
            content_checks = page.evaluate(CONTENT_CHECKS_JS)
        ctx.close()

    browser.close()
    fails = sum(
        1
        for block in overflow_report
        for r in block["results"]
        if not r.get("missing") and r.get("overflow", 0) != 0
    )
    tap_fails = sum(len(t["below44"]) for t in tap_report)
    order_ok = (
        content_checks
        and content_checks.get("pageTitle")
        == "Market briefing: Dow Jones, Nasdaq Composite, and Hang Seng gainers"
        and content_checks.get("subtitle") == "Dow Jones, Nasdaq Composite, and Hang Seng gainers"
        and content_checks.get("snapshotIndexOrder")
        == [
            "Dow Jones Industrial Average",
            "Nasdaq Composite",
            "Hang Seng Index",
        ]
    )
    content_ok = (
        content_checks
        and order_ok
        and not content_checks.get("hasNasdaqPeChart")
        and not content_checks.get("hsiPeHas2015")
        and not content_checks.get("hsiPeHas3690")
        and not content_checks.get("hsiPeHas1997")
        and not content_checks.get("tmcrHas200DayMark")
        and content_checks.get("previewBannerVisible")
    )
    hero_ok = all(not fs.get("chartsInHero") for fs in first_screen)
    return {
        "engine": browser_type,
        "overflowFails": fails,
        "tapBelow44Count": tap_fails,
        "overflow": overflow_report,
        "tapTargets": tap_report,
        "firstScreen": first_screen,
        "contentChecks": content_checks,
        "contentRulesPass": content_ok,
        "heroNoCharts": hero_ok,
        "pass": fails == 0 and tap_fails == 0 and content_ok and hero_ok,
    }


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    scanned = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    static = static_leak_checks()
    results = {"scannedAt": scanned, "html": str(HTML), "staticChecks": static, "engines": {}}

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
        "contentRulesPass": ch.get("contentRulesPass"),
        "heroNoCharts": ch.get("heroNoCharts"),
        "staticLeaks": static.get("htmlLeaks"),
        "firstScreenNotes": (lambda fs_list: {
            "320x568": {
                "dow_fraction": next((r["fraction"] for r in _rows(fs_list, "320x568") if r.get("i") == 0), None),
                "nasdaq_fraction": next((r["fraction"] for r in _rows(fs_list, "320x568") if r.get("i") == 1), None),
                "hang_seng_fraction": next((r["fraction"] for r in _rows(fs_list, "320x568") if r.get("i") == 2), None),
            },
            "320x720": {
                "dow_fraction": next((r["fraction"] for r in _rows(fs_list, "320x720") if r.get("i") == 0), None),
                "nasdaq_fraction": next((r["fraction"] for r in _rows(fs_list, "320x720") if r.get("i") == 1), None),
                "hang_seng_fraction": next((r["fraction"] for r in _rows(fs_list, "320x720") if r.get("i") == 2), None),
            },
            "667x390_hang_seng_fraction": next(
                (r["fraction"] for r in _rows(fs_list, "667x390") if r.get("i") == 2), None
            ),
        })(ch.get("firstScreen") or []),
    }
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()