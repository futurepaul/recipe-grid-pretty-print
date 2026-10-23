"""
Print-first stylesheet
======================

Generates the standalone CSS used by rendered documents. The design borrows
from recipetables.com: a warm off-white palette, monospace ingredients with
bold quantities, peach step cells with centred sans-serif text, and
full-width grey "prep" rows.

The stylesheet is tuned so the tables behave well when printed to PDF:
tables split between rows rather than through cells, headings stay with the
content which follows them, and background colours survive printing.
"""

from typing import Optional

# Paper geometry in millimetres: sheet size and the top / side / bottom
# margins used for both the @page rule and the on-screen page preview. The
# content box on screen is therefore pixel-identical to the printed content
# box, which is what makes the pagination script's measurements exact.
GEOMETRY = {
    ("a4", "portrait"): {"sheet": (210, 297), "margin": (16, 14, 18)},
    ("a4", "landscape"): {"sheet": (297, 210), "margin": (16, 14, 18)},
    ("letter", "portrait"): {"sheet": (215.9, 279.4), "margin": (14, 13, 16)},
    ("letter", "landscape"): {"sheet": (279.4, 215.9), "margin": (14, 13, 16)},
}

_PAGE_RULES = {
    "a4": "size: A4{orientation}; margin: {mt}mm {ms}mm {mb}mm;",
    "letter": "size: letter{orientation}; margin: {mt}mm {ms}mm {mb}mm;",
}


def page_geometry(paper: str, orientation: str) -> dict:
    """
    Return the page geometry (in mm) for a given paper size and orientation:
    ``sheet`` width/height, ``margin`` top/sides/bottom, and ``content``
    width/height.
    """
    try:
        geo = GEOMETRY[(paper, orientation)]
    except KeyError:
        raise ValueError(f"Unsupported paper/orientation: {paper}/{orientation}")
    mt, ms, mb = geo["margin"]
    sheet_w, sheet_h = geo["sheet"]
    return {
        "sheet_w": sheet_w,
        "sheet_h": sheet_h,
        "margin_top": mt,
        "margin_side": ms,
        "margin_bottom": mb,
        "content_w": round(sheet_w - 2 * ms, 2),
        "content_h": round(sheet_h - mt - mb, 2),
    }


def build_css(
    paper: str = "a4",
    orientation: str = "portrait",
    accent: Optional[str] = None,
) -> str:
    """
    Return the complete stylesheet for a rendered document.

    Parameters
    ==========
    paper:
        Paper size to target: ``a4`` (default) or ``letter``.
    orientation:
        ``portrait`` (default) or ``landscape``.
    accent:
        An optional CSS colour overriding the default peach used for step
        cells.
    """
    if paper not in _PAGE_RULES:
        raise ValueError(f"Unsupported paper size: {paper}")
    if orientation not in ("portrait", "landscape"):
        raise ValueError(f"Unsupported orientation: {orientation}")

    geo = page_geometry(paper, orientation)
    step_background = "var(--rgp-step-bg)" if accent is None else accent
    page_rule = _PAGE_RULES[paper].format(
        orientation="" if orientation == "portrait" else " landscape",
        mt=geo["margin_top"],
        ms=geo["margin_side"],
        mb=geo["margin_bottom"],
    )

    css = """
/* ----------------------------------------------------------------------
   recipe-grid-pretty-print stylesheet (print-first)
   ---------------------------------------------------------------------- */

:root {
    --rgp-ink: #29241f;
    --rgp-muted: #8d8579;
    --rgp-line: #e4ddd3;
    --rgp-line-strong: #4a443c;
    --rgp-page: #f1ede8;
    --rgp-sheet: #ffffff;
    --rgp-step-bg: #f9e7d7;
    --rgp-prep-bg: #f4f2ef;

    /* Exact printed content box, used by the pagination script. */
    --rgp-content-height: @CONTENT_H@mm;
    --rgp-content-width: @CONTENT_W@mm;

    --rgp-font-sans: ui-sans-serif, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    --rgp-font-mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, "Liberation Mono", monospace;
}

* {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    box-sizing: border-box;
}

html {
    background: var(--rgp-page);
    font-family: var(--rgp-font-sans);
    color: var(--rgp-ink);
    -webkit-font-smoothing: antialiased;
}

body {
    margin: 0;
    padding: 24px 16px 48px;
    overflow-x: auto;
}

/*
 * The "sheet of paper" the recipe is presented on. On screen it is the
 * exact paper size with the exact print margins, so what you see is what
 * prints (and so the pagination script measures true print geometry).
 */
.rgp-sheet {
    width: @SHEET_W@mm;
    min-height: @SHEET_H@mm;
    margin: 0 auto;
    background: var(--rgp-sheet);
    padding: @MT@mm @MS@mm @MB@mm;
    border-radius: 2px;
    box-shadow: 0 1px 3px rgba(41, 36, 31, 0.08), 0 12px 40px rgba(41, 36, 31, 0.10);
}

/* Print toolbar: hidden when printing. */
.rgp-toolbar {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--rgp-muted);
    background: var(--rgp-sheet);
    border: 1px solid var(--rgp-line);
    border-radius: 999px;
    padding: 6px 8px 6px 14px;
    box-shadow: 0 2px 10px rgba(41, 36, 31, 0.10);
}
.rgp-toolbar button {
    font: inherit;
    font-weight: 600;
    color: var(--rgp-ink);
    background: var(--rgp-step-bg);
    border: none;
    border-radius: 999px;
    padding: 5px 12px;
    cursor: pointer;
}
.rgp-toolbar button:hover {
    filter: brightness(0.97);
}

/* ----------------------------------------------------------------------
   Document typography
   ---------------------------------------------------------------------- */

.rgp-doc {
    font-size: 10.5pt;
    line-height: 1.55;
}

.rgp-doc h1 {
    font-size: 22pt;
    font-weight: 750;
    letter-spacing: -0.015em;
    line-height: 1.15;
    margin: 0 0 4pt;
}
.rgp-doc h1 .rg-serving-count {
    color: var(--rgp-muted);
    font-weight: 500;
}
.rgp-doc h2 {
    font-size: 13pt;
    font-weight: 700;
    margin: 20pt 0 6pt;
    break-after: avoid;
}
.rgp-doc h3 {
    font-size: 11pt;
    font-weight: 700;
    margin: 14pt 0 4pt;
    break-after: avoid;
}
.rgp-doc p {
    margin: 6pt 0;
    orphans: 3;
    widows: 3;
}
.rgp-doc ul, .rgp-doc ol {
    margin: 6pt 0;
    padding-left: 18pt;
}
.rgp-doc li {
    margin: 2pt 0;
}
.rgp-doc a {
    color: inherit;
}
.rgp-doc p.rgp-scaling-note {
    color: var(--rgp-muted);
    font-size: 9.5pt;
    margin: 0 0 10pt;
}
.rgp-doc .rg-original-servings, .rgp-doc .rg-scaling-factor {
    font-weight: 600;
}

/* ----------------------------------------------------------------------
   Recipe tables
   ---------------------------------------------------------------------- */

.rgp-recipe-block {
    margin: 14pt 0;
}

table.rgp {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid var(--rgp-line);
    font-family: var(--rgp-font-mono);
    font-size: 9.5pt;
    line-height: 1.5;
}

table.rgp td {
    border: 1px solid var(--rgp-line);
    padding: 8px 12px;
    margin: 0;
    vertical-align: middle;
}

/* Ingredients: monospace, quantity in bold, white background. */
table.rgp td.rgp-ingredient {
    background: var(--rgp-sheet);
}
table.rgp td.rgp-ingredient .rgp-quantity {
    font-weight: 700;
}

/* Steps: peach cells with centred sans-serif text. */
table.rgp td.rgp-step {
    background: @STEP_BACKGROUND@;
    font-family: var(--rgp-font-sans);
    font-weight: 650;
    font-size: 11pt;
    line-height: 1.4;
    text-align: center;
    padding: 14px 16px;
}

/* Prep steps: full-width grey rows above the grid. */
table.rgp td.rgp-prep {
    background: var(--rgp-prep-bg);
    padding: 7px 12px;
}
.rgp-prep-label {
    display: inline-block;
    font-family: var(--rgp-font-mono);
    font-size: 8pt;
    color: var(--rgp-muted);
    margin-right: 12px;
    vertical-align: 0.08em;
}
.rgp-prep-text {
    font-family: var(--rgp-font-sans);
    font-size: 10.5pt;
}

/* References to sub recipes elsewhere in the recipe. */
table.rgp td.rgp-reference {
    background: var(--rgp-sheet);
}
table.rgp td.rgp-reference a {
    color: inherit;
    text-decoration: none;
}
table.rgp td.rgp-reference .rgp-proportion,
table.rgp td.rgp-reference .rgp-proportion-remainder,
table.rgp td.rgp-reference .rgp-quantity {
    font-weight: 700;
}

/* Sub recipe headers (named with ':=' in the source). */
table.rgp td.rgp-sub-recipe-header {
    background: var(--rgp-prep-bg);
    font-family: var(--rgp-font-sans);
    font-weight: 700;
    text-align: center;
    letter-spacing: 0.01em;
}

/* Sub recipes with multiple named outputs: a list floating to the right
   of the grid, outside the table borders. */
table.rgp td.rgp-sub-recipe-outputs {
    border: none;
    padding: 0 0 0 14px;
}
table.rgp ul.rgp-sub-recipe-output-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-around;
    height: 100%;
}
table.rgp ul.rgp-sub-recipe-output-list li {
    font-weight: 700;
    white-space: nowrap;
}
table.rgp ul.rgp-sub-recipe-output-list li::before {
    content: "\\2192  ";
    color: var(--rgp-muted);
    font-weight: 400;
}

/* Border utilities (always applied to both sides of a shared edge). */
table.rgp td.rgp-border-top-none     { border-top: none; }
table.rgp td.rgp-border-bottom-none  { border-bottom: none; }
table.rgp td.rgp-border-left-none    { border-left: none; }
table.rgp td.rgp-border-right-none   { border-right: none; }

table.rgp td.rgp-border-top-thick    { border-top: 2px solid var(--rgp-line-strong); }
table.rgp td.rgp-border-bottom-thick { border-bottom: 2px solid var(--rgp-line-strong); }
table.rgp td.rgp-border-left-thick   { border-left: 2px solid var(--rgp-line-strong); }
table.rgp td.rgp-border-right-thick  { border-right: 2px solid var(--rgp-line-strong); }

/* Scaled values ({N} in the source), e.g. when a recipe is rescaled. */
.rgp-scaled-value {
    font-variant-numeric: tabular-nums;
}

/* Continuation cells inserted by the pagination script where a step cell
   is cut by a page break: kept short so row heights are unchanged. */
table.rgp td.rgp-continuation {
    text-align: center;
    padding: 2px 16px;
}
.rgp-continued-label {
    font-family: var(--rgp-font-sans);
    font-size: 8pt;
    font-weight: 400;
    font-style: italic;
    color: var(--rgp-muted);
}

/* A block of prep steps with no accompanying table. */
table.rgp.rgp-prep-only td {
    border-bottom: none;
}
table.rgp.rgp-prep-only tr:last-child td {
    border-bottom: 1px solid var(--rgp-line);
}

/* ----------------------------------------------------------------------
   Printing
   ---------------------------------------------------------------------- */

@page {
    @PAGE_RULE@
}

@media print {
    html, body {
        background: var(--rgp-sheet);
        padding: 0;
    }
    .rgp-sheet {
        width: auto;
        min-height: 0;
        margin: 0;
        padding: 0;
        border-radius: 0;
        box-shadow: none;
    }
    .rgp-toolbar {
        display: none;
    }

    /* Explicit page breaks stamped by the pagination script: these are the
       only places a table is allowed to split, chosen so that no cell ever
       straddles two pages. */
    .rgp-force-break {
        break-before: page;
    }

    /* Split tables between rows, never through a cell or heading. Note:
       deliberately no break-inside:avoid on cells -- the pagination script
       decides where cells may be cut, and asking the browser to keep cells
       whole makes it shove tall rowspan cells onto their own page. */
    table.rgp {
        break-inside: auto;
    }
    table.rgp tr {
        break-inside: avoid;
    }
    /* Keep sub-recipe headers with the rows that follow them. */
    table.rgp tr.rgp-header-row {
        break-after: avoid;
        break-inside: avoid;
    }
    .rgp-recipe-block {
        break-inside: auto;
    }
}

@media screen and (max-width: 640px) {
    body {
        padding: 12px 8px 32px;
    }
    table.rgp {
        font-size: 8.5pt;
    }
    table.rgp td.rgp-step {
        font-size: 9.5pt;
    }
}
"""

    return (
        css.replace("@STEP_BACKGROUND@", step_background)
        .replace("@PAGE_RULE@", page_rule)
        .replace("@CONTENT_H@", str(geo["content_h"]))
        .replace("@CONTENT_W@", str(geo["content_w"]))
        .replace("@SHEET_W@", str(geo["sheet_w"]))
        .replace("@SHEET_H@", str(geo["sheet_h"]))
        .replace("@MT@", str(geo["margin_top"]))
        .replace("@MS@", str(geo["margin_side"]))
        .replace("@MB@", str(geo["margin_bottom"]))
        .strip()
        + "\n"
    )
