#!/usr/bin/env python3
"""Retint and retype Tracie's locked Stage-1 SVGs into the v2 typographic world.

Writes copies under stage-3/mocks/figures-v3/. Does not edit stage-1 sources.
Geometry and numeric strings in the canonical (wide) copies are unchanged.
Stacked and narrow variants reflow panels or labels for readable type at
narrow widths; intra-panel geometry and numeric strings stay the same.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path("/workspace/market-brief")
SRC = ROOT / "stage-1" / "figures"
OUT = ROOT / "stage-3" / "mocks" / "figures-v3"

FONT = "Source Sans 3, Noto Sans, sans-serif"
SRC_FONT = "DejaVu Sans, Liberation Sans, Arial, sans-serif"

# v2 tokens. Rust #7c2d12 (200-day) is retinted to stone so it does not
# read as a loss colour. Shapes stay: circle = last/close, square = 50-day,
# diamond = 200-day.
COLOR = {
    "#fffefb": "#F6F4EF",
    "#1c1917": "#16181D",
    "#57534e": "#5A5E66",
    "#1e3a5f": "#16181D",  # last/close marker
    "#0f4c5c": "#3F434C",  # 50-day square
    "#7c2d12": "#8A8478",  # 200-day diamond (stone, not rust)
    "#8a9aab": "#8A8478",  # 52-week fill
    "#e7e5e4": "#EEEBE4",  # track
    "#d6d3d1": "#CFCBC3",  # rules
    "#f0eeeb": "#EEEBE4",  # grid
    "#3d4f61": "#3F434C",  # comparison bars
    "#78716c": "#6B675F",  # RSI 30/70 ticks
}

PANEL_CUTS = (0.0, 369.67, 730.33, 1100.0)
PANEL_Y0 = 68.0
PANEL_Y1 = 260.0  # includes TMCR italic note at y=252
PANEL_H = PANEL_Y1 - PANEL_Y0
STACK_GAP = 20.0
STACK_PAD = 8.0
STACK_W = 369.67

# Comparison source plot origin / width (bars start at x=200).
CMP_X0 = 200.0
CMP_W_SRC = 820.0
CMP_RIGHT_PAD = 24.0
CMP_PLOT_W = CMP_W_SRC - CMP_X0 - CMP_RIGHT_PAD  # 596


def _replace_colors(svg: str) -> str:
    def repl(m: re.Match[str]) -> str:
        attr, val = m.group(1), m.group(2)
        mapped = COLOR.get(val, COLOR.get(val.lower(), val))
        return f'{attr}="{mapped}"'

    return re.sub(r'\b(fill|stroke)="(#[0-9A-Fa-f]{6})"', repl, svg)


def restyle_canonical(svg: str) -> str:
    """Retint and retype only. Coordinates and text content stay put."""
    out = svg.replace(SRC_FONT, FONT)
    out = _replace_colors(out)
    # Stone #8A8478 is fine for the 200-day diamond (3.38:1, UI 3:1) but not
    # for the label text (needs 4.5:1). Keep the diamond; ink the words.
    def retint_200_label(m: re.Match[str]) -> str:
        return m.group(0).replace('fill="#8A8478"', 'fill="#3F434C"')

    out = re.sub(
        r"<text[^>]*>[^<]*200-day[^<]*</text>",
        retint_200_label,
        out,
    )
    return out


def _attr(el: str, name: str) -> float | None:
    m = re.search(rf'\b{name}="([^"]+)"', el)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _primary_x(el: str) -> float | None:
    tag = re.match(r"<(\w+)", el)
    if not tag:
        return None
    name = tag.group(1)
    if name == "circle":
        return _attr(el, "cx")
    if name == "rect":
        return _attr(el, "x")
    if name == "text":
        return _attr(el, "x")
    if name == "line":
        x1, x2 = _attr(el, "x1"), _attr(el, "x2")
        if x1 is None:
            return None
        if x2 is None:
            return x1
        if abs(x1 - x2) < 0.01:
            return x1
        return (x1 + x2) / 2
    if name == "polygon":
        m = re.search(r'points="([^"]+)"', el)
        if not m:
            return None
        xs = []
        for pt in m.group(1).replace(",", " ").split():
            try:
                xs.append(float(pt))
                break
            except ValueError:
                continue
        # points are x,y x,y — take first number of each pair
        vals = []
        raw = m.group(1).replace(",", " ").split()
        try:
            nums = [float(v) for v in raw]
        except ValueError:
            return None
        for i in range(0, len(nums), 2):
            vals.append(nums[i])
        return sum(vals) / len(vals) if vals else None
    return None


def _shift_element(el: str, dx: float, dy: float) -> str:
    def shift_attr(m: re.Match[str]) -> str:
        name, val = m.group(1), m.group(2)
        try:
            return f'{name}="{float(val) + (dx if name in {"x", "x1", "x2", "cx"} else dy):.2f}"'
        except ValueError:
            return m.group(0)

    el = re.sub(r'\b(x|x1|x2|cx|y|y1|y2|cy)="([^"]+)"', shift_attr, el)

    def shift_points(m: re.Match[str]) -> str:
        raw = m.group(1)
        parts = raw.replace(",", " ").split()
        nums = [float(v) for v in parts]
        out = []
        for i in range(0, len(nums), 2):
            x = nums[i] + dx
            y = nums[i + 1] + dy if i + 1 < len(nums) else 0
            out.append(f"{x:.2f},{y:.2f}")
        return 'points="' + " ".join(out) + '"'

    el = re.sub(r'points="([^"]+)"', shift_points, el)
    return el


def _iter_elements(body: str) -> list[str]:
    """Split a flat SVG body into top-level elements (no nesting in these files)."""
    return re.findall(r"<[^>]+/>|<[^>]+>.*?</[^>]+>|<[^>]+>", body, flags=re.DOTALL)


def _element_ys(el: str) -> list[float]:
    ys: list[float] = []
    for name in ("y", "y1", "y2", "cy"):
        v = _attr(el, name)
        if v is not None:
            ys.append(v)
    m = re.search(r'points="([^"]+)"', el)
    if m:
        raw = m.group(1).replace(",", " ").split()
        try:
            nums = [float(v) for v in raw]
        except ValueError:
            nums = []
        for i in range(1, len(nums), 2):
            ys.append(nums[i])
    return ys


def stack_per_name(styled: str) -> str:
    """Reflow the three side-by-side panels into a vertical stack.

    Intra-panel coordinates (relative) and text strings are preserved.
    Title/subtitle leave the visual (kept in <title>/<desc>); HTML captions
    carry the dateline. Panel height follows the content, so empty canvas
    from the original 280px frame is not stacked three times.
    """
    title_m = re.search(r"<title>(.*?)</title>", styled, re.DOTALL)
    desc_m = re.search(r"<desc>(.*?)</desc>", styled, re.DOTALL)
    title = title_m.group(1) if title_m else "Quantitative charts"
    desc = desc_m.group(1) if desc_m else ""

    start = styled.find("</desc>")
    body = styled[start + len("</desc>") : styled.rfind("</svg>")].strip()
    elements = _iter_elements(body)
    panels: list[list[str]] = [[], [], []]
    for el in elements:
        if el.startswith("<rect") and _attr(el, "width") and _attr(el, "width") >= 1099:
            continue
        if el.startswith("<line"):
            x1, x2 = _attr(el, "x1"), _attr(el, "x2")
            y1 = _attr(el, "y1") or 0
            if x1 is not None and x2 is not None and abs(x1 - x2) < 0.01:
                if abs(x1 - 369.67) < 0.1 or abs(x1 - 730.33) < 0.1:
                    if y1 >= 60:
                        continue
        x = _primary_x(el)
        y = _attr(el, "y") or _attr(el, "y1") or _attr(el, "cy") or 0
        if y and y <= 56:
            continue
        if x is None:
            continue
        if x < PANEL_CUTS[1] - 0.05:
            panels[0].append(el)
        elif x < PANEL_CUTS[2] - 0.05:
            panels[1].append(el)
        else:
            panels[2].append(el)

    # Align each panel so its left titles sit at x=20, like panel 1.
    # Panel 2/3 source titles start 11 units after the cut.
    extra_dx = [0.0, 9.0, 9.0]
    pad_top = 10.0
    pad_bot = 16.0
    gap = 16.0
    packed: list[tuple[float, float, list[tuple[str, float, float]]]] = []
    # each: height, dx, list of (el, dx, dy)
    cursor = pad_top
    total_parts: list[tuple[str, float, float, float]] = []  # el, dx, dy, rule_y or None
    rules: list[float] = []
    for i, els in enumerate(panels):
        if not els:
            continue
        ys = []
        for el in els:
            ys.extend(_element_ys(el))
        if not ys:
            continue
        y_min, y_max = min(ys), max(ys)
        # Keep a little air above the panel title (source titles at ~76)
        y0 = min(y_min, 76.0) - 4.0
        height = (y_max - y0) + pad_bot
        if i > 0:
            rules.append(cursor - gap / 2)
        dy = cursor - y0
        dx = -PANEL_CUTS[i] + extra_dx[i]
        for el in els:
            total_parts.append((el, dx, dy))
        cursor += height + (gap if i < 2 else 0)
    height = cursor + 4.0

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{STACK_W:.2f}" height="{height:.2f}" viewBox="0 0 {STACK_W:.2f} {height:.2f}" role="img" aria-labelledby="title desc">',
        f"<title>{title}</title>",
        f"<desc>{desc}</desc>",
        f'<rect width="{STACK_W:.2f}" height="{height:.2f}" fill="#F6F4EF"/>',
    ]
    for yrule in rules:
        parts.append(
            f'<line x1="16.00" y1="{yrule:.2f}" x2="{STACK_W - 16:.2f}" y2="{yrule:.2f}" stroke="#CFCBC3" stroke-width="1" stroke-linecap="round"/>'
        )
    for el, dx, dy in total_parts:
        parts.append(_shift_element(el, dx, dy))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _text_content(el: str) -> str:
    m = re.search(r">([^<]*)</text>", el)
    return m.group(1) if m else ""


def make_narrow_comparison(styled: str) -> str:
    """Label-above-bar reflow for 320–430px. Bar-length ratios and numeric
    strings are preserved. Titles/footers are omitted visually (HTML caption).
    """
    title_m = re.search(r"<title>(.*?)</title>", styled, re.DOTALL)
    desc_m = re.search(r"<desc>(.*?)</desc>", styled, re.DOTALL)
    title = title_m.group(1) if title_m else "Comparison chart"
    desc = desc_m.group(1) if desc_m else ""

    start = styled.find("</desc>")
    body = styled[start + len("</desc>") : styled.rfind("</svg>")].strip()
    elements = _iter_elements(body)

    bars = []
    labels_by_y: list[tuple[float, str, str]] = []  # y, text, el
    values: list[tuple[float, str, str]] = []
    ticks: list[tuple[float, str]] = []  # x, label
    axis_caption = ""

    for el in elements:
        if el.startswith("<rect") and _attr(el, "width") and _attr(el, "width") >= 819:
            continue
        if el.startswith("<rect"):
            x, y, w, h = _attr(el, "x"), _attr(el, "y"), _attr(el, "width"), _attr(el, "height")
            if x is not None and abs(x - 200) < 0.2 and w and h and h <= 16:
                bars.append((y or 0, w, el))
            continue
        if el.startswith("<text"):
            x, y = _attr(el, "x") or 0, _attr(el, "y") or 0
            content = _text_content(el)
            # chart title/subtitles at the top
            if y <= 70:
                continue
            # footer wrapped notes (start at x=24, y>=400-ish or y after axis)
            # axis caption is mid-x around 496, font 10
            # tick labels are middle-anchored at the tick x, y around 380/296
            if 'text-anchor="end"' in el and x >= 170 and x <= 200:
                labels_by_y.append((y, content, el))
                continue
            if 'text-anchor="start"' in el and x >= 200:
                # value at end of bar, or in-bar end-anchor is text-anchor=end with fill paper
                values.append((y, content, el))
                continue
            if 'text-anchor="end"' in el and x > 200:
                # in-bar values (fill paper)
                values.append((y, content, el))
                continue
            if 'text-anchor="middle"' in el and abs(x - 496) < 1 and "Percentage" in content or (
                'text-anchor="middle"' in el and abs(x - 496) < 1
            ):
                if "Percentage" in content or content == "Market value" or content.startswith("Trailing"):
                    axis_caption = content
                    continue
            if 'text-anchor="middle"' in el and 100 < x:
                # tick label
                if content and not content.startswith("Bar length") and "not on this chart" not in content:
                    if "Percentage" in content or content == "Market value" or content.startswith("Trailing"):
                        axis_caption = content
                    else:
                        ticks.append((x, content))
                continue
            # leftover footer
            continue
        # lines: grid / axis
        continue

    bars.sort(key=lambda t: t[0])
    labels_by_y.sort(key=lambda t: t[0])
    values.sort(key=lambda t: t[0])

    # Pair each bar with the closest label and value by y (bar y+10 ~ label y)
    rows = []
    for by, bw, _el in bars:
        def closest(items: list[tuple[float, str, str]]) -> tuple[str, float]:
            if not items:
                return ("", 0)
            best = min(items, key=lambda it: abs(it[0] - (by + 10)))
            return best[1], best[0]

        label, _ = closest(labels_by_y)
        value, _ = closest(values)
        rows.append((label, value, bw))

    # Layout
    W = 360.0
    pad = 12.0
    plot_w = W - 2 * pad
    row_h = 40.0
    top = 8.0
    n = len(rows)
    axis_y = top + n * row_h + 6
    footer_y = axis_y + 28
    height = footer_y + 12

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}" height="{height:.2f}" viewBox="0 0 {W:.2f} {height:.2f}" role="img" aria-labelledby="title desc">',
        f"<title>{title}</title>",
        f"<desc>{desc}</desc>",
        f'<rect width="{W:.2f}" height="{height:.2f}" fill="#F6F4EF"/>',
    ]
    # baseline at 0
    y0_line_top = top + 4
    y0_line_bot = top + n * row_h - 8
    parts.append(
        f'<line x1="{pad:.2f}" y1="{y0_line_top:.2f}" x2="{pad:.2f}" y2="{y0_line_bot:.2f}" stroke="#CFCBC3" stroke-width="1" stroke-linecap="round"/>'
    )
    # light ticks
    for tx, tlabel in ticks:
        frac = (tx - CMP_X0) / CMP_PLOT_W
        if frac < 0 or frac > 1.05:
            continue
        x = pad + frac * plot_w
        parts.append(
            f'<line x1="{x:.2f}" y1="{y0_line_top:.2f}" x2="{x:.2f}" y2="{y0_line_bot:.2f}" stroke="#EEEBE4" stroke-width="1" stroke-linecap="round"/>'
        )

    for i, (label, value, bw) in enumerate(rows):
        y = top + i * row_h
        text_y = y + 14
        bar_y = y + 20
        bar_w = (bw / CMP_PLOT_W) * plot_w
        parts.append(
            f'<text x="{pad:.2f}" y="{text_y:.2f}" font-family="{FONT}" font-size="12" font-weight="normal" fill="#16181D" text-anchor="start">{label}</text>'
        )
        parts.append(
            f'<text x="{W - pad:.2f}" y="{text_y:.2f}" font-family="{FONT}" font-size="12" font-weight="600" fill="#16181D" text-anchor="end">{value}</text>'
        )
        if bar_w < 0.5:
            bar_w = 0.5
        parts.append(
            f'<rect x="{pad:.2f}" y="{bar_y:.2f}" width="{bar_w:.2f}" height="10.00" rx="2" fill="#3F434C"/>'
        )

    # tick labels, staggered if needed
    if ticks:
        for i, (tx, tlabel) in enumerate(ticks):
            frac = (tx - CMP_X0) / CMP_PLOT_W
            if frac < -0.02 or frac > 1.08:
                continue
            x = pad + frac * plot_w
            ty = axis_y + 12 + (10 if i % 2 else 0)
            parts.append(
                f'<text x="{x:.2f}" y="{ty:.2f}" font-family="{FONT}" font-size="9" font-weight="normal" fill="#5A5E66" text-anchor="middle">{tlabel}</text>'
            )
        height = axis_y + 32
        # rewrite height by not — we'll fix after; for now extend if staggered
        if len(ticks) > 2:
            height = axis_y + 36

    parts.append("</svg>")
    # Fix viewBox height to match computed
    svg = "\n".join(parts) + "\n"
    svg = re.sub(
        r'width="360.00" height="[^"]+" viewBox="0 0 360.00 [^"]+"',
        f'width="360.00" height="{height:.2f}" viewBox="0 0 360.00 {height:.2f}"',
        svg,
        count=1,
    )
    svg = re.sub(
        r'<rect width="360.00" height="[^"]+" fill="#F6F4EF"/>',
        f'<rect width="360.00" height="{height:.2f}" fill="#F6F4EF"/>',
        svg,
        count=1,
    )
    return svg


def extract_text_strings(svg: str) -> list[str]:
    return re.findall(r"<text[^>]*>([^<]*)</text>", svg)


def numeric_tokens(texts: list[str]) -> list[str]:
    toks: list[str] = []
    for t in texts:
        toks.extend(
            re.findall(
                r"(?:HK\$|US\$)?[+]?\d[\d,]*(?:\.\d+)?%?|(?:−|-)\d[\d,]*(?:\.\d+)?%?",
                t,
            )
        )
    return toks


def run() -> None:
    if OUT.exists():
        # only clear our outputs, not other dirs
        for sub in (OUT / "per-name", OUT / "comparisons"):
            if sub.exists():
                shutil.rmtree(sub)
            sub.mkdir(parents=True)
    else:
        (OUT / "per-name").mkdir(parents=True)
        (OUT / "comparisons").mkdir(parents=True)

    mismatches: list[str] = []
    n_wide = n_stack = n_narrow = 0

    for src in sorted((SRC / "per-name").glob("*.svg")):
        raw = src.read_text(encoding="utf-8")
        styled = restyle_canonical(raw)
        dest = OUT / "per-name" / src.name
        dest.write_text(styled, encoding="utf-8")
        n_wide += 1
        src_nums = numeric_tokens(extract_text_strings(raw))
        dst_nums = numeric_tokens(extract_text_strings(styled))
        if src_nums != dst_nums:
            mismatches.append(f"{src.name} canonical numbers {src_nums} vs {dst_nums}")
        # geometry: all numeric attributes except fill/stroke/font should match
        # (colours changed). Compare x/y/width/height/cx/cy/r/points/x1/y1/x2/y2.
        def geom(s: str) -> list[str]:
            return re.findall(
                r'\b(?:x|y|x1|y1|x2|y2|cx|cy|r|rx|width|height|points)="[^"]+"', s
            )

        if geom(raw) != geom(styled):
            mismatches.append(f"{src.name} canonical geometry changed")
        stacked = stack_per_name(styled)
        stack_path = OUT / "per-name" / src.name.replace(".svg", "-stack.svg")
        stack_path.write_text(stacked, encoding="utf-8")
        n_stack += 1
        # Body texts only (y > 56): titles/subtitles are cropped from the visual
        # and kept in <title>/<desc> plus the HTML caption.
        def body_texts(svg: str) -> list[str]:
            out = []
            for el in re.findall(r"<text[^>]*>[^<]*</text>", svg):
                y = _attr(el, "y") or _attr(el, "y1") or 99
                if y > 56:
                    out.append(_text_content(el))
            return out
        src_body = numeric_tokens(body_texts(raw))
        st_nums = numeric_tokens(extract_text_strings(stacked))
        if sorted(st_nums) != sorted(src_body):
            mismatches.append(
                f"{src.name} stack numbers {st_nums} vs source body {src_body}"
            )

    for src in sorted((SRC / "comparisons").glob("*.svg")):
        raw = src.read_text(encoding="utf-8")
        styled = restyle_canonical(raw)
        dest = OUT / "comparisons" / src.name
        dest.write_text(styled, encoding="utf-8")
        n_wide += 1
        src_nums = numeric_tokens(extract_text_strings(raw))
        dst_nums = numeric_tokens(extract_text_strings(styled))
        if src_nums != dst_nums:
            mismatches.append(f"{src.name} canonical numbers {src_nums} vs {dst_nums}")

        def geom(s: str) -> list[str]:
            return re.findall(
                r'\b(?:x|y|x1|y1|x2|y2|cx|cy|r|rx|width|height|points)="[^"]+"', s
            )

        if geom(raw) != geom(styled):
            mismatches.append(f"{src.name} canonical geometry changed")
        narrow = make_narrow_comparison(styled)
        narrow_path = OUT / "comparisons" / src.name.replace(".svg", "-narrow.svg")
        narrow_path.write_text(narrow, encoding="utf-8")
        n_narrow += 1
        # Row labels, bar values, and axis tick labels must remain.
        # Title, subtitle, and footer notes are provided as HTML captions.
        def cmp_body_texts(svg: str) -> list[str]:
            out = []
            for el in re.findall(r"<text[^>]*>[^<]*</text>", svg):
                y = _attr(el, "y") or 0
                x = _attr(el, "x") or 0
                content = _text_content(el)
                if y <= 70:
                    continue
                if content.startswith("Bar length") or "not on this chart" in content:
                    continue
                if content.startswith("No trailing P/E is shown"):
                    continue
                if content.startswith("Trailing P/E (") or content == "Market value" or content.startswith("Percentage change"):
                    continue
                out.append(content)
            return out
        src_body = numeric_tokens(cmp_body_texts(raw))
        # Keep value and tick numbers; axis caption "last 12 months" is HTML.
        nar_nums = numeric_tokens(extract_text_strings(narrow))
        missing = [n for n in src_body if n not in nar_nums]
        # Drop numbers that only appear in the axis-caption sentence (e.g. "12 months")
        # when that caption was moved to HTML.
        if missing:
            # allow missing if the only leftover is from a mid-page axis caption
            mismatches.append(f"{src.name} narrow missing numbers {missing} (src body {src_body})")

    if mismatches:
        raise SystemExit("Restyle verification failed:\n" + "\n".join(mismatches))
    print(f"Wrote {n_wide} canonical, {n_stack} stacked, {n_narrow} narrow under {OUT}")


if __name__ == "__main__":
    run()
