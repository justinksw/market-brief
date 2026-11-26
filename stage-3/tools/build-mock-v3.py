#!/usr/bin/env python3
"""Build the Stage-3 v3 static HTML mock from the locked Stage-1 report.md.

Typesets the report and places the locked, restyled charts. Does not rewrite
figures, names, verdicts, captions, or sources. Does not overwrite v1 or v2 HTML.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "stage-1" / "report.md"
OUT = ROOT / "docs" / "index.html"
FIGURES = ROOT / "stage-3" / "mocks" / "figures-v3"

EXACT_TITLE = "Market briefing: Hang Seng, Dow Jones, and Nasdaq Composite gainers"
DISPLAY_TITLE = "Market briefing"
DISPLAY_SUBTITLE = "Hang Seng, Dow Jones, and Nasdaq Composite gainers"
SHORT_ASOF = (
    "As of Thursday 26 November 2026, about 09:39 HKT "
    "(20:39 ET on Wednesday 25 November)."
)
DISCLAIMER = "This is a market briefing, not investment advice."
RETRIEVAL_SENTENCE = (
    "Figures retrieved between 09:54:26 and 09:54:51 HKT "
    "(20:54 ET on 25 November)."
)

INDEX_IDS = {
    "Hang Seng Index": "hang-seng",
    "Dow Jones Industrial Average": "dow-jones",
    "Nasdaq Composite": "nasdaq",
}

NAV = [
    ("#snapshot", "Index snapshot"),
    ("#how-to-read", "How to read"),
    ("#hang-seng", "Hang Seng"),
    ("#dow-jones", "Dow Jones"),
    ("#nasdaq", "Nasdaq"),
    ("#sources", "Sources"),
]

HEADING_RE = re.compile(
    r"^(?P<rank>\d+)\.\s+(?P<name>.+?)\s+\((?P<ticker>[^)]+)\)\s+—\s+(?P<pct>\S+)\s*$"
)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
MONEY = r"(?:HK\$|US\$)[0-9][0-9,]*(?:\.[0-9]+)?"

# Locked chart files (restyled copies). Tickers match report.md headings.
NAME_CHART = {
    "2015.HK": "2015.HK-quantitative",
    "3690.HK": "3690.HK-quantitative",
    "0857.HK": "0857.HK-quantitative",
    "0883.HK": "0883.HK-quantitative",
    "1378.HK": "1378.HK-quantitative",
    "0992.HK": "0992.HK-quantitative",
    "2899.HK": "2899.HK-quantitative",
    "1347.HK": "1347.HK-quantitative",
    "1177.HK": "1177.HK-quantitative",
    "1997.HK": "1997.HK-quantitative",
    "IBM": "IBM-quantitative",
    "NKE": "NKE-quantitative",
    "DIS": "DIS-quantitative",
    "SHW": "SHW-quantitative",
    "HD": "HD-quantitative",
    "CRM": "CRM-quantitative",
    "V": "V-quantitative",
    "TRV": "TRV-quantitative",
    "MMM": "MMM-quantitative",
    "UNH": "UNH-quantitative",
    "BGLC": "BGLC-quantitative",
    "RADX": "RADX-quantitative",
    "NRSN": "NRSN-quantitative",
    "LONA": "LONA-quantitative",
    "RAYA": "RAYA-quantitative",
    "FCUV": "FCUV-quantitative",
    "NXAT": "NXAT-quantitative",
    "ALGS": "ALGS-quantitative",
    "TMCR": "TMCR-quantitative",
    "BYAH": "BYAH-quantitative",
}

INDEX_CHARTS = {
    "Hang Seng Index": [
        ("hsi-pct-change", "Hang Seng Index: percentage change among the top 10"),
        ("hsi-market-value", "Hang Seng Index: market value among the top 10"),
        ("hsi-trailing-pe", "Hang Seng Index: trailing P/E among names that have one"),
    ],
    "Dow Jones Industrial Average": [
        ("djia-pct-change", "Dow Jones Industrial Average: percentage change among the top 10"),
        ("djia-market-value", "Dow Jones Industrial Average: market value among the top 10"),
        ("djia-trailing-pe", "Dow Jones Industrial Average: trailing P/E among names that have one"),
    ],
    "Nasdaq Composite": [
        ("nasdaq-pct-change", "Nasdaq Composite: percentage change among the top 10"),
        ("nasdaq-market-value", "Nasdaq Composite: market value among the top 10"),
    ],
}

# Public captions, meaning locked to stage-1/chart-captions.md.
CAPTION_HK_NAME = (
    "Thursday 26 Nov 2026 morning last (delayed), not an official close "
    "· Hong Kong dollars (HKD)"
)
CAPTION_US_NAME = (
    "Wednesday 25 Nov 2026 official regular-session close · US dollars (USD)"
)
CAPTION_TMCR = (
    CAPTION_US_NAME
    + ". No 200-day average is shown for this name. Only 162 official daily closes "
    "were available, fewer than 200, so the 200-day mark is omitted."
)
MARKET_SCALE = (
    "The length of each bar uses a scale that can show both the largest and the "
    "smallest company on that list. Read the labeled amounts for the actual size. "
    "A bar that looks twice as long is not necessarily twice as large."
)
CAPTION_BY_FILE = {
    "hsi-pct-change": (
        "Thursday 26 November 2026 morning last (delayed), not an official close, "
        "versus Wednesday 25 November’s official close. Amounts are in Hong Kong "
        "dollars in the briefing; the bars here show the percentage change."
    ),
    "djia-pct-change": (
        "Wednesday 25 November official regular-session close versus Tuesday 24 "
        "November official close, in US dollars."
    ),
    "nasdaq-pct-change": (
        "Wednesday 25 November official regular-session close versus Tuesday 24 "
        "November official close, in US dollars."
    ),
    "hsi-market-value": (
        "Thursday 26 November 2026 morning last (delayed), not an official close, "
        "versus Wednesday 25 November’s official close, in Hong Kong dollars. "
        + MARKET_SCALE
    ),
    "djia-market-value": (
        "Wednesday 25 November official regular-session close versus Tuesday 24 "
        "November official close, in US dollars. " + MARKET_SCALE
    ),
    "nasdaq-market-value": (
        "Wednesday 25 November official regular-session close versus Tuesday 24 "
        "November official close, in US dollars. " + MARKET_SCALE
    ),
    "hsi-trailing-pe": (
        "Thursday 26 November 2026 morning last (delayed), not an official close. "
        "Seven of the ten names have a trailing P/E on this chart. No trailing P/E "
        "is shown for Li Auto (2015.HK), Meituan (3690.HK), or Wharf REIC (1997.HK), "
        "so those three names are not on the chart. Li Auto reported a net loss for "
        "the third quarter."
    ),
    "djia-trailing-pe": (
        "Wednesday 25 November official regular-session close. All ten names have "
        "a trailing P/E, and all ten appear."
    ),
}

CHART_GLOSSARY = [
    (
        "The charts in this briefing.",
        "Each of the 30 top gainers has one three-part chart: the 52-week range, the 14-day RSI, and the last price or official close versus the 50-day and the 200-day averages. "
        "For Hang Seng names, the marker labeled “Last” is the Thursday 26 November 2026 morning last price (a delayed quote, not the day’s official close). The 50-day and 200-day averages, and the 14-day RSI, still use official closes through Wednesday 25 November only, so the Thursday last is being compared with levels that stop at Wednesday’s official close. "
        "For Dow and Nasdaq names, the marker labeled “Close” is the official regular-session close on Wednesday 25 November 2026. The averages and the RSI use the same official-close series through that Wednesday. "
        "The 50-day and 200-day averages and the 14-day RSI use official regular-session closes through Wednesday 25 November 2026 only. Thursday 26 November Hang Seng last prices are not included in those averages or in the RSI. The daily history used for those figures was retrieved on 26 November 2026, 10:56:51–10:56:59 HKT (25 November, 21:56 ET).",
    ),
    (
        "52-week range chart.",
        "The bar runs from the low of the past year to the high of the past year. The marker shows where the already-published last price (Hang Seng) or official close (Dow and Nasdaq) sits between those two points. “Near the low,” “mid-range,” or “near the high” has the same meaning as in the briefing.",
    ),
    (
        "14-day RSI chart.",
        "This is a 0–100 gauge of how strongly a share has risen or fallen over the past two weeks of official closes, ending on Wednesday 25 November. Marks are shown near 30 and 70, as in the briefing: readings near 70 or higher mean recent gains have been strong; readings near 30 or lower mean recent declines have been strong. It describes recent movement; it is not a forecast.",
    ),
    (
        "Last or close versus the 50-day and 200-day averages.",
        "The 50-day and 200-day averages are the average official closing prices over the past 50 and 200 trading days, ending on Wednesday 25 November. A last price or official close above an average is higher than that recent typical level; one below it is lower. No 200-day average is shown for The Metals Royalty Company (TMCR). Only 162 official daily closes were available, fewer than 200, so the 200-day mark is omitted.",
    ),
    (
        "Percentage change among the top 10.",
        "These three charts show the already-published percentage change for each name in that index’s top 10, in the same rank order as the briefing. A rise of 4.31% means the last price or official close is 4.31% higher than the prior official close.",
    ),
    (
        "Market value among the top 10.",
        "These three charts show each company’s size on that index’s top 10 list: the share price multiplied by the number of shares, in the listing currency (Hong Kong dollars for Hang Seng names; US dollars for Dow and Nasdaq names). The length of each bar uses a scale that can show both the largest and the smallest company on that list. Read the labeled amounts for the actual size. A bar that looks twice as long is not necessarily twice as large.",
    ),
    (
        "Trailing P/E, where a figure is shown.",
        "Trailing P/E is the share price divided by the company’s earnings over the last 12 months. A higher figure means investors are paying more for each dollar of recent profit. Hang Seng: seven of the ten names have a trailing P/E on this chart. No trailing P/E is shown for Li Auto (2015.HK), Meituan (3690.HK), or Wharf REIC (1997.HK), so those three names are not on the chart. Li Auto reported a net loss for the third quarter. Dow Jones Industrial Average: all ten names have a trailing P/E, and all ten appear. Nasdaq Composite: no trailing P/E is shown for any of the ten names, so there is no Nasdaq trailing P/E chart.",
    ),
]


def inline_svg(path: Path, css_class: str) -> str:
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<\?xml[^>]+\?>", "", raw).strip()
    raw = re.sub(r"<svg\b", f'<svg class="{css_class}"', raw, count=1)
    return raw


def crop_wide_comparison(svg: str) -> str:
    """Hide in-SVG title, subtitle, and footer notes; HTML supplies those."""

    def keep(el: str) -> bool:
        if not el.startswith("<text"):
            return True
        y = 0.0
        m = re.search(r'\by="([^"]+)"', el)
        if m:
            try:
                y = float(m.group(1))
            except ValueError:
                y = 0
        if y <= 70:
            return False
        text_m = re.search(r">([^<]*)</text>", el)
        content = text_m.group(1) if text_m else ""
        if content.startswith("Bar length") or content.startswith("amounts;"):
            return False
        if content.startswith("No trailing P/E") or content.startswith("not on this chart"):
            return False
        if content.startswith("Percentage change versus"):
            return False
        if content == "Market value" or content.startswith("Trailing P/E (share"):
            return False
        return True

    # Split elements inside svg
    start = svg.find("<svg")
    open_end = svg.find(">", start)
    head = svg[: open_end + 1]
    body = svg[open_end + 1 : svg.rfind("</svg>")]
    # keep title/desc
    kept = []
    for el in re.findall(r"<title>.*?</title>|<desc>.*?</desc>|<[^>]+/>|<[^>]+>.*?</[^>]+>|<[^>]+>", body, flags=re.DOTALL):
        if el.startswith("<title") or el.startswith("<desc"):
            kept.append(el)
            continue
        if el.startswith("<rect") and re.search(r'width="820', el):
            # leave the paper field but we will crop viewBox
            kept.append(el)
            continue
        if keep(el):
            kept.append(el)
    # Crop viewBox to start at y=70, end just below tick labels
    ys = []
    for el in kept:
        for attr in ("y", "y1", "y2"):
            m = re.search(rf'\b{attr}="([^"]+)"', el)
            if m:
                try:
                    ys.append(float(m.group(1)))
                except ValueError:
                    pass
    y1 = max(ys) + 16 if ys else 400
    # rewrite svg open tag viewBox / height
    head = re.sub(r'viewBox="[^"]+"', f'viewBox="0 70 820 {y1 - 70:.2f}"', head)
    head = re.sub(r'\bheight="[^"]+"', f'height="{y1 - 70:.2f}"', head)
    return head + "\n" + "\n".join(kept) + "\n</svg>"


def render_name_chart(ticker: str) -> str:
    key = NAME_CHART[ticker]
    path = FIGURES / "per-name" / f"{key}-stack.svg"
    if not path.exists():
        raise SystemExit(f"Missing name chart: {path}")
    svg = inline_svg(path, "chart-stack")
    if ticker == "TMCR":
        caption = CAPTION_TMCR
    elif ticker.endswith(".HK"):
        caption = CAPTION_HK_NAME
    else:
        caption = CAPTION_US_NAME
    return (
        f'<figure class="name-chart">'
        f'<div class="chart-frame">{svg}</div>'
        f'<figcaption class="chart-caption">{esc(caption)}</figcaption>'
        f"</figure>"
    )


def render_index_charts(title: str) -> str:
    items = INDEX_CHARTS[title]
    parts = ['<div class="index-charts">']
    for key, heading in items:
        wide_path = FIGURES / "comparisons" / f"{key}.svg"
        narrow_path = FIGURES / "comparisons" / f"{key}-narrow.svg"
        if not wide_path.exists() or not narrow_path.exists():
            raise SystemExit(f"Missing comparison chart: {key}")
        wide = crop_wide_comparison(inline_svg(wide_path, "chart-wide-svg"))
        # ensure class chart-wide on wrapper, not just svg
        wide = wide.replace('<svg class="chart-wide-svg"', '<svg class="chart-wide-svg chart-wide"', 1)
        narrow = inline_svg(narrow_path, "chart-narrow")
        caption = CAPTION_BY_FILE[key]
        parts.append("<figure class='chart-figure'>")
        parts.append(f"<h3 class='chart-title'>{esc(heading)}</h3>")
        parts.append(f'<div class="chart-frame">{wide}{narrow}</div>')
        parts.append(f"<figcaption class='chart-caption'>{esc(caption)}</figcaption>")
        parts.append("</figure>")
    parts.append("</div>")
    return "\n".join(parts)



def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    parts: list[str] = []
    last = 0
    for m in BOLD_RE.finditer(text):
        parts.append(esc(text[last : m.start()]))
        parts.append("<strong>")
        parts.append(esc(m.group(1)))
        parts.append("</strong>")
        last = m.end()
    parts.append(esc(text[last:]))
    return "".join(parts)


def wrap_signed(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        token = m.group(0)
        kind = "chg-up" if token.startswith("+") else "chg-down"
        return f'<span class="chg {kind}">{esc(token)}</span>'

    return re.sub(r"[+−][0-9][0-9,.]*%?", repl, text)


def parse_blocks(md: str) -> list[tuple[str, str, str]]:
    lines = md.replace("\r\n", "\n").split("\n")
    blocks: list[tuple[str, str, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip(), ""))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip(), ""))
            i += 1
            continue
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip(), ""))
            i += 1
            continue
        if line.strip() == "---":
            blocks.append(("hr", "", ""))
            i += 1
            continue
        if line.startswith("|"):
            buf = [line]
            i += 1
            while i < n and lines[i].startswith("|"):
                buf.append(lines[i])
                i += 1
            blocks.append(("table", "", "\n".join(buf)))
            continue
        if line.strip() == "":
            i += 1
            continue
        buf = [line]
        i += 1
        while (
            i < n
            and lines[i].strip() != ""
            and not lines[i].startswith("#")
            and not lines[i].startswith("|")
            and lines[i].strip() != "---"
        ):
            buf.append(lines[i])
            i += 1
        blocks.append(("p", "", "\n".join(buf)))
    return blocks


def split_label(paragraph: str, labels: tuple[str, ...]) -> tuple[str, str] | None:
    for label in labels:
        token = f"**{label}**"
        if paragraph.startswith(token):
            rest = paragraph[len(token) :].lstrip()
            return label, rest
    return None


def parse_table(raw: str) -> tuple[list[str], list[list[str]]]:
    rows = []
    for line in raw.split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    headers = rows[0]
    data = [
        r
        for r in rows[1:]
        if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in r)
    ]
    return headers, data


def slug_stock(ticker: str, rank: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "-", ticker).strip("-").lower()
    return f"name-{safe}-{rank}"


def split_opening(paragraph: str) -> tuple[str, str, str, str]:
    """Split the opening paragraph typographically.

    Returns (short_asof, retrieval_sentence, method_notes, disclaimer).
    Times and facts are taken from the source; the retrieval clause is
    recapitalised as its own sentence after being moved out of the hero.
    """
    raw = paragraph.replace("**", "")
    if not raw.endswith(DISCLAIMER):
        raise SystemExit("As-of paragraph does not end with the locked disclaimer.")
    body = raw[: -len(DISCLAIMER)].rstrip()
    if not body.endswith("."):
        raise SystemExit("Opening body does not end with a period.")

    prefix = (
        "As of Thursday 26 November 2026, about 09:39 HKT "
        "(20:39 ET on Wednesday 25 November), with figures retrieved between "
        "09:54:26 and 09:54:51 HKT (20:54 ET on 25 November). "
    )
    if not body.startswith(prefix):
        raise SystemExit(f"Opening as-of/retrieval clause did not match.\nGot: {body[:240]!r}")
    method = body[len(prefix) :].strip()
    if not method:
        raise SystemExit("Method notes missing after as-of split.")
    return SHORT_ASOF, RETRIEVAL_SENTENCE, method, DISCLAIMER


def change_percent(cell: str) -> str | None:
    m = re.search(r"[+−][0-9][0-9,.]*%", cell.replace("**", ""))
    return m.group(0) if m else None


def extract_figures(quant_first: str) -> list[tuple[str, str]]:
    """Pull a compact figure row from the first Quantitative paragraph.

    Every value is a verbatim substring of that paragraph. Missing figures
    are omitted, never invented.
    """
    items: list[tuple[str, str]] = []
    t = quant_first

    m = re.search(rf"\b(Last|Closed) ({MONEY})", t)
    if not m:
        raise SystemExit(f"No Last/Closed price in: {t[:120]!r}")
    items.append((m.group(1), m.group(2)))

    m = re.search(rf"\bup ({MONEY}) from ", t)
    if not m:
        raise SystemExit(f"No up-amount in: {t[:120]!r}")
    items.append(("Change", "up " + m.group(1)))

    m = re.search(rf"from (?:Wednesday’s official close of )?({MONEY})", t)
    if not m:
        raise SystemExit(f"No prior price in: {t[:160]!r}")
    items.append(("Prior", m.group(1)))

    if "Session so far:" in t:
        m = re.search(
            rf"Session so far: open ({MONEY}), high ({MONEY}), low ({MONEY})", t
        )
        if not m:
            raise SystemExit(f"HK session open/high/low failed: {t[:200]!r}")
        items.append(("Open", m.group(1)))
        items.append(("High", m.group(2)))
        items.append(("Low", m.group(3)))
    else:
        m = re.search(
            rf"Session high ({MONEY}), low ({MONEY}), open ({MONEY})", t
        )
        if not m:
            raise SystemExit(f"US session high/low/open failed: {t[:200]!r}")
        items.append(("High", m.group(1)))
        items.append(("Low", m.group(2)))
        items.append(("Open", m.group(3)))

    m = re.search(
        rf"Market value about ((?:HK\$|US\$)[0-9][0-9,]*(?:\.[0-9]+)?(?: million| billion| trillion)?)",
        t,
    )
    if not m:
        raise SystemExit(f"Market value failed: {t[:200]!r}")
    items.append(("Market value", "about " + m.group(1)))

    if re.search(r"No trailing P/E is shown", t):
        items.append(("Trailing P/E", "No trailing P/E is shown"))
    else:
        m = re.search(r"Trailing P/E ([0-9]+(?:\.[0-9]+)?)", t)
        if not m:
            raise SystemExit(f"Trailing P/E failed: {t[:200]!r}")
        items.append(("Trailing P/E", m.group(1)))

    m = re.search(rf"52-week range ({MONEY}–{MONEY})", t)
    if not m:
        raise SystemExit(f"52-week range failed: {t[:200]!r}")
    items.append(("52-week", m.group(1)))

    m = re.search(
        r"(?:About|Volume) ((?:[0-9][0-9,]*(?:\.[0-9]+)?(?: million)?|[0-9][0-9,]*) shares)",
        t,
    )
    if not m:
        raise SystemExit(f"Volume failed: {t[:220]!r}")
    vol = m.group(1)
    if t[m.start() :].startswith("About"):
        items.append(("Volume", "About " + vol))
    else:
        items.append(("Volume", vol))

    # Sanity: every value is in the source paragraph
    for label, val in items:
        if val not in t and not (label == "Change" and val[3:] in t):
            # "up HK$4.56" — "up HK$4.56 from" is in t; "up " + money is in t
            if val not in t:
                raise SystemExit(f"Extracted value not in source ({label}): {val!r}")
    return items


def render_figure_row(items: list[tuple[str, str]]) -> str:
    cells = []
    for label, val in items:
        cells.append(
            "<div class='fig'>"
            f"<span class='fig-label'>{esc(label)}</span>"
            f"<span class='fig-value'>{wrap_signed(esc(val))}</span>"
            "</div>"
        )
    return "<div class='figure-row'>" + "".join(cells) + "</div>"


def render_snapshot(headers: list[str], rows: list[list[str]], notes: list[str]) -> str:
    thead = "".join(f"<th scope='col'>{esc(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        tds = []
        pct = change_percent(row[3]) if len(row) > 3 else None
        for i, cell in enumerate(row):
            label = headers[i] if i < len(headers) else ""
            if i == 0:
                badge = ""
                if pct:
                    kind = "chg-up" if pct.startswith("+") else "chg-down"
                    badge = (
                        f'<span class="index-pct"><span class="chg {kind}">'
                        f"{esc(pct)}</span></span>"
                    )
                tds.append(
                    f'<th scope="row" class="index-name">{inline(cell)}{badge}</th>'
                )
            else:
                value = wrap_signed(inline(cell))
                tds.append(
                    f'<td data-label="{esc(label)}">'
                    f'<span class="field-label">{esc(label)}</span>'
                    f'<span class="field-value">{value}</span>'
                    f"</td>"
                )
        body_rows.append("<tr>" + "".join(tds) + "</tr>")
    notes_html = "".join(f"<p>{inline(p)}</p>" for p in notes)
    nav_items = "".join(
        f'<li><a href="{esc(href)}">{esc(label)}</a></li>' for href, label in NAV
    )
    return f"""
<div class="snapshot wrap-wide">
  <table class="snapshot-table">
    <caption>Index snapshot</caption>
    <thead>
      <tr>{thead}</tr>
    </thead>
    <tbody>
      {''.join(body_rows)}
    </tbody>
  </table>
</div>
<nav class="toc toc-after-snapshot" aria-label="Briefing sections">
  <ul>
    {nav_items}
  </ul>
</nav>
<div class="lead backdrop">{notes_html}</div>
"""


def render_glossary(items: list[tuple[str, str]], retrieval: str, method: str) -> str:
    parts = [
        '<div class="method-block">',
        f"<p class='retrieval'>{esc(retrieval)}</p>",
        "<details class='method-details'>",
        "<summary>Price type, session hours, time zones, and currencies</summary>",
        f"<div class='details-body'><p>{inline(method)}</p></div>",
        "</details>",
        "</div>",
        '<div class="glossary">',
    ]
    for term, definition in items:
        parts.append("<details class='glossary-item'>")
        parts.append(f"<summary>{esc(term)}</summary>")
        parts.append(f"<div class='details-body'><p>{inline(definition)}</p></div>")
        parts.append("</details>")
    for term, definition in CHART_GLOSSARY:
        parts.append("<details class='glossary-item'>")
        parts.append(f"<summary>{esc(term)}</summary>")
        parts.append(f"<div class='details-body'><p>{inline(definition)}</p></div>")
        parts.append("</details>")
    parts.append("</div>")
    return "\n".join(parts)


def render_stock(heading: str, verdict: str, quant: list[str], qual: list[str]) -> str:
    m = HEADING_RE.match(heading)
    if not m:
        raise SystemExit(f"Unparseable stock heading: {heading!r}")
    rank = m.group("rank")
    name = m.group("name")
    ticker = m.group("ticker")
    pct = m.group("pct")
    sid = slug_stock(ticker, rank)
    kind = "chg-up" if pct.startswith("+") else "chg-down"
    if not quant:
        raise SystemExit(f"No Quantitative paragraphs for {heading!r}")
    figures = extract_figures(quant[0])
    fig_html = render_figure_row(figures)
    quant_ps = "".join(f"<p>{inline(p)}</p>" for p in quant)
    qual_ps = "".join(f"<p>{inline(p)}</p>" for p in qual)
    return f"""
<article class="stock" id="{esc(sid)}" data-ticker="{esc(ticker)}">
  <header class="stock-head">
    <span class="stock-rank">{esc(rank)}.</span>
    <h3 class="stock-name">{esc(name)}</h3>
    <p class="stock-ticker">{esc(ticker)}</p>
    <p class="stock-pct"><span class="chg {kind}">{esc(pct)}</span></p>
  </header>
  <section class="verdict" aria-label="Verdict">
    <span class="block-label">Verdict.</span>
    <div class="block-body"><p>{inline(verdict)}</p></div>
  </section>
  {fig_html}
  <section class="quant" aria-label="Quantitative">
    <span class="block-label">Quantitative.</span>
    {render_name_chart(ticker)}
    <div class="block-body prose-quiet">{quant_ps}</div>
  </section>
  <section class="qual" aria-label="Qualitative">
    <span class="block-label">Qualitative.</span>
    <div class="block-body prose-quiet">{qual_ps}</div>
  </section>
</article>
"""


def render_index(
    title: str, lead_paras: list[str], takeaway: str, list_lead: str, stocks: list[str]
) -> str:
    sid = INDEX_IDS[title]
    lead_html = ""
    if lead_paras:
        lead_html += f'<p class="up-count">{inline(lead_paras[0])}</p>'
        for p in lead_paras[1:]:
            lead_html += f'<div class="lead"><p>{inline(p)}</p></div>'
    takeaway_html = ""
    if takeaway:
        takeaway_html = f"""
<div class="takeaway">
  <span class="takeaway-label">Takeaway.</span>
  <div class="takeaway-body"><p>{inline(takeaway)}</p></div>
</div>
"""
    list_html = f'<p class="list-lead">{inline(list_lead)}</p>' if list_lead else ""
    charts_html = render_index_charts(title)
    return f"""
<section class="section" id="{sid}">
  <div class="wrap">
    <h2 class="section-title">{esc(title)}</h2>
    {lead_html}
    {takeaway_html}
  </div>
  <div class="wrap wrap-wide">
    {charts_html}
  </div>
  <div class="wrap">
    {list_html}
    <div class="stock-list">
      {''.join(stocks)}
    </div>
  </div>
</section>
"""


def build() -> str:
    md = REPORT.read_text(encoding="utf-8")
    if not md.endswith("\n"):
        md += "\n"
    blocks = parse_blocks(md)
    it = iter(enumerate(blocks))

    def next_block():
        for i, b in it:
            return b
        return None

    b = next_block()
    assert b and b[0] == "h1" and b[1] == EXACT_TITLE, b

    b = next_block()
    assert b and b[0] == "p"
    short_asof, retrieval, method, disclaimer = split_opening(b[2])

    b = next_block()
    assert b and b[0] == "h2" and b[1] == "Index snapshot"

    b = next_block()
    assert b and b[0] == "table"
    headers, rows = parse_table(b[2])

    snap_notes: list[str] = []
    b = next_block()
    while b and b[0] == "p":
        snap_notes.append(b[2])
        b = next_block()

    assert b and b[0] == "h2" and b[1] == "How to read these figures", b

    glossary: list[tuple[str, str]] = []
    b = next_block()
    while b and b[0] == "p":
        split = split_label(
            b[2],
            (
                "Last price and official close.",
                "Open, high, and low.",
                "Change.",
                "Market value (market cap).",
                "Trailing P/E.",
                "52-week range.",
                "Volume.",
                "50-day and 200-day averages.",
                "14-day RSI.",
                "Other company and market figures.",
            ),
        )
        if not split:
            raise SystemExit(f"Unparseable glossary paragraph: {b[2][:80]!r}")
        glossary.append(split)
        b = next_block()
    if b and b[0] == "hr":
        b = next_block()

    indexes_html: list[str] = []
    while b and b[0] == "h2" and b[1] != "Sources":
        title = b[1]
        if title not in INDEX_IDS:
            raise SystemExit(f"Unexpected index heading: {title!r}")
        lead_paras: list[str] = []
        takeaway = ""
        list_lead = ""
        stocks_html: list[str] = []
        b = next_block()
        while b and b[0] == "p":
            split = split_label(b[2], ("Takeaway.",))
            if split:
                takeaway = split[1]
            elif not takeaway:
                lead_paras.append(b[2])
            else:
                list_lead = (list_lead + "\n" + b[2]).strip() if list_lead else b[2]
            b = next_block()
        while b and b[0] == "h3":
            heading = b[1]
            verdict = ""
            quant: list[str] = []
            qual: list[str] = []
            mode = None
            b = next_block()
            while b and b[0] == "p":
                split = split_label(b[2], ("Verdict.", "Quantitative.", "Qualitative."))
                if split:
                    label, rest = split
                    if label == "Verdict.":
                        mode = "verdict"
                        verdict = rest
                    elif label == "Quantitative.":
                        mode = "quant"
                        if rest:
                            quant.append(rest)
                    else:
                        mode = "qual"
                        if rest:
                            qual.append(rest)
                else:
                    if mode == "quant":
                        quant.append(b[2])
                    elif mode == "qual":
                        qual.append(b[2])
                    elif mode == "verdict":
                        verdict = (verdict + " " + b[2]).strip()
                    else:
                        raise SystemExit(f"Loose paragraph in stock {heading}: {b[2][:80]!r}")
                b = next_block()
            if not verdict or not quant or not qual:
                raise SystemExit(
                    f"Incomplete stock block for {heading!r}: V={bool(verdict)} Q={len(quant)} L={len(qual)}"
                )
            stocks_html.append(render_stock(heading, verdict, quant, qual))
        indexes_html.append(render_index(title, lead_paras, takeaway, list_lead, stocks_html))
        if b and b[0] == "hr":
            b = next_block()

    assert b and b[0] == "h2" and b[1] == "Sources", b
    sources: list[str] = []
    b = next_block()
    while b and b[0] == "p":
        sources.append(b[2])
        b = next_block()
    if b is not None:
        raise SystemExit(f"Unexpected trailing block after Sources: {b!r}")

    snapshot_html = render_snapshot(headers, rows, snap_notes)
    glossary_html = render_glossary(glossary, retrieval, method)
    sources_html = "".join(f"<p>{inline(p)}</p>" for p in sources)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(EXACT_TITLE)}</title>
  <meta name="description" content="{esc(EXACT_TITLE)}. {esc(disclaimer)}">
  <link rel="stylesheet" href="fonts.css">
  <link rel="stylesheet" href="market-brief-v3.css">
</head>
<body>
  <p class="preview-banner" role="note"><span class="preview-banner-label">PREVIEW</span></p>
  <a class="skip-link" href="#main">Skip to briefing</a>
  <header class="masthead-wrap" id="top">
    <div class="wrap">
      <header class="masthead">
        <h1 class="masthead-title">{esc(DISPLAY_TITLE)}</h1>
        <p class="masthead-subtitle">{esc(DISPLAY_SUBTITLE)}</p>
        <p class="dateline"><strong>{esc(short_asof[:short_asof.index(' (')])}</strong>{esc(short_asof[short_asof.index(' ('):])}</p>
        <p class="disclaimer">{esc(disclaimer)}</p>
      </header>
    </div>
  </header>
  <main id="main">
    <section class="section section-snapshot" id="snapshot">
      <div class="wrap wrap-wide">
        <h2 class="section-title">Index snapshot</h2>
        {snapshot_html}
      </div>
    </section>
    <section class="section" id="how-to-read">
      <div class="wrap">
        <h2 class="section-title">How to read these figures</h2>
        {glossary_html}
      </div>
    </section>
    {''.join(indexes_html)}
    <section class="section" id="sources">
      <div class="wrap">
        <h2 class="section-title">Sources</h2>
        <div class="sources-body prose-quiet">
          {sources_html}
        </div>
        <footer class="page-foot">
          <a class="back-top" href="#top">Back to top</a>
        </footer>
      </div>
    </section>
  </main>
</body>
</html>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"Indexes: {len(indexes_html)}, glossary {len(glossary)}, sources {len(sources)}")
    return doc


if __name__ == "__main__":
    build()
