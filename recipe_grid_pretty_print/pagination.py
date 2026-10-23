"""
Deterministic pagination
========================

Browsers paginate HTML tables by slicing them between rows, but cells which
span many rows (a step covering all of its ingredients) end up straddling a
page boundary -- the cell is fragmented mid-span, its background bleeding
from one page onto the next.

This module embeds a small script into generated documents which makes
pagination deterministic and straddle-free:

1. The on-screen "sheet" is laid out at exactly the printed paper size with
   the same margins as the ``@page`` rule, so element geometry measured in
   the browser matches what the printer will produce.

2. On load, the script simulates the page flow (the page's content height
   comes from the ``--rgp-content-height`` CSS variable) and stamps an
   explicit ``break-before: page`` (the ``rgp-force-break`` class) exactly
   where pages will break.

3. Table rows are grouped into atomic blocks (rows joined by a rowspan cell,
   header/prep rows glued to the row that follows) which are kept whole
   wherever they fit on a page.

4. When a break must cut through a tall block, every cell whose rowspan
   crosses the break is split: its rowspan is shortened to the rows before
   the break and a "(continued)" cell is inserted in the same grid column on
   the next page. No cell ever straddles two pages.

The script is idempotent: it restores any previous splits and re-computes on
``beforeprint``.
"""

PAGINATION_JS = """
(function () {
  "use strict";

  var FORCE_CLASS = "rgp-force-break";
  var CONTINUATION_CLASS = "rgp-continuation";
  var ORIGINAL_SPAN_ATTR = "data-rgp-original-rowspan";
  /* Printed layout drifts slightly from measured screen layout (fractional
     border/rounding accumulate per row), so capacity is pessimistic. */
  var SAFETY_PX = 12;
  var ROW_EPSILON = 0.6;

  /* --------------------------------------------------------------------
   * Restoration (pagination is re-run idempotently)
   * -------------------------------------------------------------------- */

  function restore() {
    var continuations = document.querySelectorAll("td." + CONTINUATION_CLASS);
    for (var i = 0; i < continuations.length; i++) {
      continuations[i].parentNode.removeChild(continuations[i]);
    }
    var split = document.querySelectorAll("td[" + ORIGINAL_SPAN_ATTR + "]");
    for (var j = 0; j < split.length; j++) {
      var cell = split[j];
      cell.rowSpan = parseInt(cell.getAttribute(ORIGINAL_SPAN_ATTR), 10);
      cell.removeAttribute(ORIGINAL_SPAN_ATTR);
    }
    var forced = document.querySelectorAll("." + FORCE_CLASS);
    for (var k = 0; k < forced.length; k++) {
      forced[k].classList.remove(FORCE_CLASS);
    }
  }

  /* --------------------------------------------------------------------
   * Page capacity
   * -------------------------------------------------------------------- */

  function contentHeightPx() {
    var probe = document.createElement("div");
    probe.style.position = "absolute";
    probe.style.visibility = "hidden";
    probe.style.height = "var(--rgp-content-height)";
    document.body.appendChild(probe);
    var h = probe.getBoundingClientRect().height;
    probe.parentNode.removeChild(probe);
    return h - SAFETY_PX;
  }

  /* --------------------------------------------------------------------
   * Table structure
   * -------------------------------------------------------------------- */

  /*
   * Group table row indices into atomic blocks: rows connected by a rowspan
   * cell share a block, and header/prep rows are glued to the row which
   * follows them. Returns a list of [firstRow, lastRow] pairs plus, for
   * each row, the index of its block and whether it starts one.
   */
  function rowBlocks(rows) {
    var n = rows.length;
    var pairs = [];
    var blockOf = new Array(n);
    var starts = {};
    var start = 0;
    var reach = 0;
    for (var r = 0; r < n; r++) {
      if (r > reach) {
        pairs.push([start, reach]);
        start = r;
        reach = r;
      }
      starts[r] = r === start;
      var row = rows[r];
      for (var c = 0; c < row.cells.length; c++) {
        var span = row.cells[c].rowSpan;
        if (span > 1 && r + span - 1 > reach) {
          reach = r + span - 1;
        }
      }
      if ((row.classList.contains("rgp-header-row") ||
           row.classList.contains("rgp-prep-row")) &&
          r + 1 < n && r + 1 > reach) {
        reach = r + 1;
      }
    }
    if (n > 0) {
      pairs.push([start, reach]);
    }
    for (var b = 0; b < pairs.length; b++) {
      for (var r2 = pairs[b][0]; r2 <= pairs[b][1]; r2++) {
        blockOf[r2] = b;
      }
    }
    return { pairs: pairs, blockOf: blockOf, isBlockStart: starts };
  }

  function tableMetrics(table) {
    var rows = table.rows;
    var tableTop = table.getBoundingClientRect().top;
    var tops = [];
    var bottoms = [];
    for (var r = 0; r < rows.length; r++) {
      var rect = rows[r].getBoundingClientRect();
      tops.push(rect.top - tableTop);
      bottoms.push(rect.bottom - tableTop);
    }
    var rb = rowBlocks(rows);
    var blockHeights = rb.pairs.map(function (p) {
      return bottoms[p[1]] - tops[p[0]];
    });
    return {
      table: table,
      rows: rows,
      tops: tops,
      bottoms: bottoms,
      blocks: rb.pairs,
      blockOf: rb.blockOf,
      isBlockStart: rb.isBlockStart,
      blockHeights: blockHeights
    };
  }

  /* --------------------------------------------------------------------
   * Grid columns (for inserting continuation cells in the right column)
   * -------------------------------------------------------------------- */

  function gridColumnOf(table, targetRow, targetCell) {
    var occupied = [];
    for (var r = 0; r <= targetRow; r++) {
      occupied[r] = occupied[r] || {};
      var row = table.rows[r];
      var c = 0;
      for (var i = 0; i < row.cells.length; i++) {
        while (occupied[r][c]) c++;
        var cell = row.cells[i];
        if (cell === targetCell) return c;
        for (var dr = 0; dr < cell.rowSpan; dr++) {
          for (var dc = 0; dc < cell.colSpan; dc++) {
            if (!occupied[r + dr]) occupied[r + dr] = {};
            occupied[r + dr][c + dc] = true;
          }
        }
        c += cell.colSpan;
      }
    }
    return -1;
  }

  /*
   * Split every cell whose rowspan crosses row k: shorten it to the rows
   * before the break and insert a "(continued)" cell in the same grid
   * column in row k.
   */
  function splitCellsAt(table, k) {
    var crossings = [];
    for (var r = 0; r < k; r++) {
      var row = table.rows[r];
      for (var c = 0; c < row.cells.length; c++) {
        var cell = row.cells[c];
        if (cell.rowSpan > 1 && r + cell.rowSpan - 1 >= k) {
          crossings.push({ cell: cell, row: r, column: gridColumnOf(table, r, cell) });
        }
      }
    }
    for (var i = 0; i < crossings.length; i++) {
      insertContinuation(table, crossings[i], k);
    }
  }

  function insertContinuation(table, crossing, k) {
    var cell = crossing.cell;
    var originalSpan = cell.rowSpan;
    if (!cell.hasAttribute(ORIGINAL_SPAN_ATTR)) {
      cell.setAttribute(ORIGINAL_SPAN_ATTR, originalSpan);
    }
    cell.rowSpan = k - crossing.row;

    var continuation = document.createElement("td");
    continuation.className = cell.className + " " + CONTINUATION_CLASS;
    continuation.colSpan = cell.colSpan;
    continuation.rowSpan = crossing.row + originalSpan - k;
    var label = document.createElement("span");
    label.className = "rgp-continued-label";
    label.appendChild(document.createTextNode("continued"));
    continuation.appendChild(label);

    var newRow = table.rows[k];
    var col = crossing.column;
    var cc = 0;
    for (var i = 0; i < newRow.cells.length; i++) {
      if (cc >= col) {
        newRow.insertBefore(continuation, newRow.cells[i]);
        return;
      }
      cc += newRow.cells[i].colSpan;
    }
    newRow.appendChild(continuation);
  }

  /* --------------------------------------------------------------------
   * Flow simulation and break insertion
   * -------------------------------------------------------------------- */

  function forceBreakBefore(el) {
    // If a heading immediately precedes the element (possibly one level up
    // through a recipe block), break before the heading instead so the
    // heading is not stranded at the bottom of a page.
    var prev = el.previousElementSibling;
    var inBlock = el.parentElement &&
      el.parentElement.classList.contains("rgp-recipe-block");
    if (inBlock && el === el.parentElement.children[0]) {
      var blockPrev = el.parentElement.previousElementSibling;
      if (blockPrev && /^H[1-6]$/.test(blockPrev.tagName)) {
        blockPrev.classList.add(FORCE_CLASS);
        return;
      }
    }
    if (prev && /^H[1-6]$/.test(prev.tagName)) {
      prev.classList.add(FORCE_CLASS);
    } else {
      el.classList.add(FORCE_CLASS);
    }
  }

  function paginate() {
    var doc = document.querySelector(".rgp-doc");
    if (!doc) return;

    restore();

    var cap = contentHeightPx();
    if (!(cap > 0)) return;

    // Flatten the document into flow units: plain elements and tables.
    var units = [];
    var children = doc.children;
    for (var i = 0; i < children.length; i++) {
      var el = children[i];
      if (el.classList && el.classList.contains("rgp-recipe-block")) {
        for (var j = 0; j < el.children.length; j++) {
          if (el.children[j].tagName === "TABLE") {
            units.push({ el: el.children[j], isTable: true });
          }
        }
      } else {
        units.push({ el: el, isTable: false });
      }
    }

    var cursor = 0;  // y position within the current page, in px

    for (var u = 0; u < units.length; u++) {
      var unit = units[u];
      var rect = unit.el.getBoundingClientRect();
      var gap = 0;
      if (cursor !== 0 && u > 0) {
        gap = rect.top - units[u - 1].el.getBoundingClientRect().bottom;
        if (!(gap > 0)) gap = 0;
      }

      if (unit.isTable) {
        cursor = paginateTable(unit.el, cursor, gap, cap);
      } else {
        var h = rect.height;
        if (cursor + gap + h <= cap) {
          cursor += gap + h;
        } else if (h <= cap) {
          // Move the whole element to the next page.
          forceBreakBefore(unit.el);
          cursor = h;
        } else {
          // Element taller than a page (long prose): model the browser
          // splitting it across the boundary.
          if (cursor + gap < cap) {
            cursor = gap + h - (cap - cursor);
          } else {
            cursor = h;
          }
        }
      }
    }
  }

  function paginateTable(table, cursor, gap, cap) {
    var m = tableMetrics(table);
    if (m.rows.length === 0) return cursor;

    // If the first atomic block fits on a page of its own but not in the
    // space remaining here, start the table on a fresh page. (Blocks taller
    // than a page are left to the walk below, which starts them in the
    // remaining space and breaks inside them.)
    if (cursor > 0 &&
        m.blockHeights[0] + cursor + gap > cap &&
        m.blockHeights[0] <= cap) {
      forceBreakBefore(table);
      cursor = 0;
      gap = 0;
    }

    // Walk the rows, tracking where the current page begins in
    // table-relative coordinates (origin).
    var origin = m.tops[0] - cursor - gap;
    var lastRow = m.rows.length - 1;
    var pageStartRow = 0;

    for (var r = 1; r <= lastRow; r++) {
      var consumed = m.bottoms[r] - origin + ROW_EPSILON * (r - pageStartRow);
      if (consumed > cap) {
        // Overflow: prefer breaking at the start of an atomic block
        // (keeping steps with their ingredients) unless that block alone
        // is taller than a page, in which case break here to fill the
        // page.
        var k = r;
        var block = m.blockOf[r];
        if (m.blockHeights[block] <= cap) {
          var start = m.blocks[block][0];
          if (start > pageStartRow && m.tops[start] > origin) {
            k = start;
          }
        }
        forceBreakAt(m, k);
        origin = m.tops[k];
        pageStartRow = k;
      }
    }

    return m.bottoms[lastRow] - origin;
  }

  function forceBreakAt(m, k) {
    m.rows[k].classList.add(FORCE_CLASS);
    splitCellsAt(m.table, k);
  }

  function run() {
    try {
      paginate();
    } catch (e) {
      /* Pagination is an enhancement: never break the document. */
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(run);
  }
  window.addEventListener("beforeprint", run);
})();
"""


def pagination_script() -> str:
    """Return a complete ``<script>`` element for embedding in a document."""
    return f"<script>\n{PAGINATION_JS}</script>"
