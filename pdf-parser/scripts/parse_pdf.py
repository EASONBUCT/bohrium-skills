#!/usr/bin/env python3
"""Parse a research PDF into structured, evidence-mapped JSON.

Primary extraction: pdftotext -tsv (word-level coordinates + text), then
pure-Python layout analysis:
  - group words into lines and blocks
  - detect multi-column layout and correct reading order
  - identify headings, paragraphs, captions, equations, tables, references
  - reconstruct tables into rows/columns
  - attach page + bounding-box evidence to every element

Usage:
  python parse_pdf.py --pdf paper.pdf --out paper.parsed.json
  python parse_pdf.py --pdf paper.pdf --out -            # stdout

Exit 0 on success (even partial), 1 when the PDF cannot be opened.
"""

import argparse
import json
import math
import re
import subprocess
import sys

# ---------------------------------------------------------------- extraction

def run_pdftotext_tsv(pdf_path):
    """Return pdftotext -tsv output, or None if pdftotext is unavailable."""
    try:
        r = subprocess.run(
            ["pdftotext", "-tsv", pdf_path, "-"],
            capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return None
        return r.stdout
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001
        return None


def parse_tsv(text):
    """Parse pdftotext -tsv into pages -> blocks -> lines -> words."""
    pages = []
    cur_page = None
    cur_block = None
    cur_line = None
    for raw in text.splitlines():
        if not raw or raw.startswith("level\t"):
            continue
        cols = raw.split("\t")
        if len(cols) < 12:
            continue
        try:
            level = int(cols[0])
        except ValueError:
            continue
        if level == 1:  # ###PAGE###
            cur_page = {"page": int(cols[1]), "blocks": []}
            pages.append(cur_page)
            cur_block = None
            cur_line = None
        elif level == 3:  # ###FLOW### (a block / paragraph)
            if cur_page is None:
                continue
            cur_block = {"lines": [], "bbox": None}
            cur_page["blocks"].append(cur_block)
            cur_line = None
        elif level == 4:  # ###LINE###
            if cur_block is None:
                continue
            cur_line = {"words": [], "bbox": None}
            cur_block["lines"].append(cur_line)
        elif level == 5:  # word
            if cur_line is None:
                continue
            try:
                w = {
                    "text": cols[11],
                    "left": float(cols[6]), "top": float(cols[7]),
                    "width": float(cols[8]), "height": float(cols[9]),
                    "conf": float(cols[10]),
                }
            except (IndexError, ValueError):
                continue
            cur_line["words"].append(w)
    # prune empty structures
    for p in pages:
        p["blocks"] = [b for b in p["blocks"] if b["lines"]]
    return [p for p in pages if p["blocks"]]


def line_bbox(line):
    if line["bbox"] is None:
        ws = line["words"]
        x0 = min(w["left"] for w in ws)
        y0 = min(w["top"] for w in ws)
        x1 = max(w["left"] + w["width"] for w in ws)
        y1 = max(w["top"] + w["height"] for w in ws)
        line["bbox"] = [x0, y0, x1, y1]
    return line["bbox"]


def line_text(line):
    ws = sorted(line["words"], key=lambda w: w["left"])
    if not ws:
        return ""
    # use the line's own word gap distribution to decide where spaces are
    gaps = []
    for i in range(1, len(ws)):
        gap = ws[i]["left"] - (ws[i - 1]["left"] + ws[i - 1]["width"])
        gaps.append(gap)
    if not gaps:
        return ws[0]["text"]
    med = sorted(gaps)[len(gaps) // 2]
    line_h = max(w["height"] for w in ws)
    space_thresh = max(1.5, min(med * 0.6 if med > 0 else line_h * 0.15, line_h * 0.25))
    out = [ws[0]["text"]]
    for i in range(1, len(ws)):
        gap = gaps[i - 1]
        if gap > space_thresh:
            out.append(" ")
        out.append(ws[i]["text"])
    return "".join(out)


def block_bbox(block):
    if block["bbox"] is None:
        xs = []
        ys = []
        for ln in block["lines"]:
            x0, y0, x1, y1 = line_bbox(ln)
            xs += [x0, x1]
            ys += [y0, y1]
        block["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
    return block["bbox"]


def block_text(block):
    return "\n".join(line_text(ln) for ln in block["lines"])


def block_max_height(block):
    return max((line_bbox(ln)[3] - line_bbox(ln)[1]) for ln in block["lines"])


# ---------------------------------------------------------------- layout

def detect_columns(page, page_width):
    """Cluster block x-centers into 1 or 2 columns. Returns (centers, labels)."""
    centers = []
    for b in page["blocks"]:
        x0, _, x1, _ = block_bbox(b)
        centers.append((x0 + x1) / 2.0)
    if not centers:
        return 1, [0] * len(page["blocks"])
    # 2 columns when there is a clear bimodal split around page center
    mid = page_width / 2.0
    left = [c for c in centers if c < mid]
    right = [c for c in centers if c >= mid]
    # only split when both sides are substantially populated and well separated
    if left and right:
        left_mean = sum(left) / len(left)
        right_mean = sum(right) / len(right)
        if right_mean - left_mean > page_width * 0.18:
            labels = [0 if c < mid else 1 for c in centers]
            return 2, labels
    return 1, [0] * len(page["blocks"])


def reading_order(page, page_width):
    ncol, labels = detect_columns(page, page_width)
    ordered = []
    for col in range(ncol):
        idxs = [i for i, lab in enumerate(labels) if lab == col]
        idxs.sort(key=lambda i: block_bbox(page["blocks"][i])[1])  # by top
        ordered.extend(idxs)
    return ordered


# ---------------------------------------------------------------- classify

HEADING_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)*)\s*[\.\s]?\s+(.{1,120})$|"
    r"^(Abstract|Introduction|Conclusions?|Discussion|Results?|Methods?|"
    r"Experiments?|Materials?|Background|Related Work|Summary|Outlook|"
    r"References|Bibliography|Acknowledgm?ents?|Appendix|Appendices|"
    r"Supplementary)\b",
    re.IGNORECASE,
)
CAPTION_RE = re.compile(
    r"^\s*(Fig\.?|Figure|Table|Scheme|Algorithm|Chart|Eq\.?|Equation)\s*\.?\s*(\d+)",
    re.IGNORECASE,
)
REF_RE = re.compile(r"^\s*(\[\d+\]|\d+\.)\s+")
EQ_RE = re.compile(r"^\s*(\(\d+\)|[A-Za-z].*=\s*.*)\s*$")
MATH_SYMBOLS = re.compile(r"[=\u2212\u2211\u222b\u221a\u03b1\u03b2\u03b3\u03b4\u03bb\u03c3\u03c0\u00b1\u00d7\u2264\u2265]")


def classify_block(block, page_height, page_width, body_height, is_margin=False):
    x0, y0, x1, y1 = block_bbox(block)
    text = block_text(block).strip()
    h = block_max_height(block)
    n_words = sum(len(ln["words"]) for ln in block["lines"])

    if not text:
        return "empty"

    # header / footer: repeated across pages at the very top or bottom
    if is_margin:
        return "margin"

    # caption
    if CAPTION_RE.match(text):
        return "caption"

    # heading: numbered/known pattern checked before the font-size title rule
    if HEADING_RE.match(text):
        return "heading"

    # title: first page, near the very top, notably larger than body text
    if y0 < page_height * 0.10 and body_height > 0 and h >= body_height * 1.25:
        return "title"

    # equation: centered + short + math-ish
    center = (x0 + x1) / 2.0
    if (abs(center - page_width / 2.0) < page_width * 0.18
            and n_words <= 20 and (EQ_RE.match(text) or MATH_SYMBOLS.search(text))):
        return "equation"

    # heading by font size (no numeric prefix, e.g. "Conclusions")
    if body_height > 0 and h >= body_height * 1.18 and n_words <= 20:
        return "heading"

    # reference entry
    if REF_RE.match(text):
        return "reference"

    # table: several lines whose words align into columns
    if len(block["lines"]) >= 3 and looks_like_table(block):
        return "table"

    return "paragraph"


def looks_like_table(block):
    """A block is table-like when several lines share large inter-word gaps
    (column gutters) that never appear in running prose."""
    lines = block["lines"]
    if len(lines) < 3:
        return False
    gaps = []
    for ln in lines:
        ws = sorted(ln["words"], key=lambda w: w["left"])
        if len(ws) < 2:
            return False
        for i in range(1, len(ws)):
            gaps.append(ws[i]["left"] - (ws[i - 1]["left"] + ws[i - 1]["width"]))
    if not gaps:
        return False
    med = sorted(gaps)[len(gaps) // 2]
    if med <= 0:
        return False
    # a column gutter is both much larger than the median word gap and wide in points
    large = [g for g in gaps if g > med * 2.5 and g > 10.0]
    return len(large) >= 2


def reconstruct_table(block):
    """Rebuild a table block into rows of cells by x-column clustering."""
    lines = block["lines"]
    all_words = [w for ln in lines for w in ln["words"]]
    xs = sorted({round(w["left"], 1) for w in all_words})
    # cluster column starts
    cols = []
    for x in xs:
        if cols and x - cols[-1] < 9.0:
            continue
        cols.append(x)
    rows = []
    for ln in sorted(lines, key=lambda l: line_bbox(l)[1]):
        cells = []
        for i, cx in enumerate(cols):
            end = cols[i + 1] - 4 if i + 1 < len(cols) else 10**9
            ws = [w for w in ln["words"] if cx - 3 <= w["left"] < end]
            ws.sort(key=lambda w: w["left"])
            cells.append(" ".join(w["text"] for w in ws))
        rows.append(cells)
    return {"columns": len(cols), "rows": rows}


def detect_grid_tables(page):
    """Detect grid-aligned clusters of cell-like blocks; return (table_dicts, drop_idx)."""
    cells = []
    for bi, b in enumerate(page["blocks"]):
        n_lines = len(b["lines"])
        n_words = sum(len(ln["words"]) for ln in b["lines"])
        if n_lines == 1 and 1 <= n_words <= 3:
            txt = block_text(b).strip()
            if HEADING_RE.match(txt) or CAPTION_RE.match(txt):
                continue
            x0, y0, x1, y1 = block_bbox(b)
            cells.append((bi, x0, y0, x1, y1, txt))
    if len(cells) < 6:
        return [], set()

    # cluster y-tops into rows, x-lefts into columns
    def cluster(vals, tol):
        ordered = sorted(set(vals))
        groups = []
        for v in ordered:
            if groups and v - groups[-1][-1] < tol:
                groups[-1].append(v)
            else:
                groups.append([v])
        return [g for g in groups if len(g) >= 1]

    row_ys = cluster([c[2] for c in cells], 6.0)
    col_xs = cluster([c[1] for c in cells], 8.0)
    if len(row_ys) < 2 or len(col_xs) < 2:
        return [], set()

    def assign(v, groups):
        for gi, g in enumerate(groups):
            if abs(v - g[0]) < 1 or (g[0] - 1 <= v <= g[-1] + 1):
                return gi
        return None

    # build row x col grid
    grid = {}
    drop = set()
    for bi, x0, y0, x1, y1, txt in cells:
        ri = assign(y0, row_ys)
        ci = assign(x0, col_xs)
        if ri is None or ci is None:
            continue
        grid.setdefault(ri, {})[ci] = txt
        drop.add(bi)

    nrows = max(grid.keys()) + 1
    ncols = max(max(d.keys()) for d in grid.values()) + 1
    rows = []
    for ri in range(nrows):
        rows.append([grid.get(ri, {}).get(ci, "") for ci in range(ncols)])

    # require reasonably dense grid (>= 70% cells filled)
    filled = sum(1 for d in grid.values() for v in d.values() if v)
    if filled < 0.7 * nrows * ncols:
        return [], set()

    table = {
        "page": page["page"],
        "bbox": [round(min(c[1] for c in cells), 1), round(min(c[2] for c in cells), 1),
                 round(max(c[3] for c in cells), 1), round(max(c[4] for c in cells), 1)],
        "grid": {"columns": ncols, "rows": rows},
    }
    return [table], drop


# ---------------------------------------------------------------- assemble

def _norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def detect_margin_keys(pages, page_height=792.0):
    """Text that repeats at the very top or bottom across >=2 pages is a
    running header/footer. Returns the set of normalized margin texts."""
    from collections import Counter
    keys = Counter()
    for p in pages:
        seen = set()
        for b in p["blocks"]:
            x0, y0, x1, y1 = block_bbox(b)
            if y0 < page_height * 0.06 or y1 > page_height * 0.94:
                t = _norm(block_text(b))
                if t and t not in seen:
                    keys[t] += 1
                    seen.add(t)
    return {k for k, c in keys.items() if c >= 2}


def assemble(pages):
    """Walk pages in reading order and build sections/tables/figures/equations/refs."""
    out_blocks = []
    sections = []
    tables = []
    figures = []
    equations = []
    references = []

    heights = [block_max_height(b) for p in pages for b in p["blocks"]]
    body_height = statistics_median(heights) if heights else 0.0
    margin_keys = detect_margin_keys(pages)

    for p in pages:
        page_h = 792.0
        page_w = 612.0
        grid_tables, drop_idx = detect_grid_tables(p)
        order = reading_order(p, page_w)
        for i, bi in enumerate(order):
            if bi in drop_idx:
                continue
            b = p["blocks"][bi]
            x0, y0, x1, y1 = block_bbox(b)
            is_margin = _norm(block_text(b)) in margin_keys and (
                y0 < page_h * 0.06 or y1 > page_h * 0.94)
            typ = classify_block(b, page_h, page_w, body_height, is_margin)
            txt = block_text(b).strip()
            entry = {
                "id": "p%d-b%d" % (p["page"], bi),
                "type": typ,
                "text": txt,
                "page": p["page"],
                "bbox": [round(v, 1) for v in (x0, y0, x1, y1)],
                "order": i,
            }
            out_blocks.append(entry)

            if typ == "heading":
                m = HEADING_RE.match(txt)
                level = 1
                if m and m.group(1):
                    level = len(m.group(1).split("."))
                sections.append({
                    "id": "sec-%d" % (len(sections) + 1),
                    "level": level,
                    "title": txt,
                    "page": p["page"],
                    "bbox": entry["bbox"],
                })
            elif typ == "title":
                entry["type"] = "title"
                sections.insert(0, {
                    "id": "sec-0",
                    "level": 0,
                    "title": txt,
                    "page": p["page"],
                    "bbox": entry["bbox"],
                })
            elif typ == "table":
                tables.append({
                    "id": "tab-%d" % (len(tables) + 1),
                    "page": p["page"],
                    "bbox": entry["bbox"],
                    "grid": reconstruct_table(b),
                    "text": txt,
                })
            elif typ == "caption":
                m = CAPTION_RE.match(txt)
                kind = m.group(1).lower() if m else "caption"
                if kind.startswith("fig"):
                    figures.append({"id": "fig-%d" % (len(figures) + 1),
                                    "caption": txt, "page": p["page"], "bbox": entry["bbox"]})
                elif kind.startswith("tab"):
                    tables.append({"id": "tab-%d" % (len(tables) + 1),
                                   "caption_only": True, "caption": txt,
                                   "page": p["page"], "bbox": entry["bbox"]})
            elif typ == "equation":
                equations.append({"id": "eq-%d" % (len(equations) + 1),
                                  "text": txt, "page": p["page"], "bbox": entry["bbox"]})
            elif typ == "reference":
                references.append({"id": "ref-%d" % (len(references) + 1),
                                   "text": txt, "page": p["page"], "bbox": entry["bbox"]})

        # add grid-detected tables (cells that were separate blocks)
        for gt in grid_tables:
            gt["id"] = "tab-%d" % (len(tables) + 1)
            tables.append(gt)

    return {
        "blocks": out_blocks,
        "sections": sections,
        "tables": tables,
        "figures": figures,
        "equations": equations,
        "references": references,
    }


def statistics_median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0.0
    if n % 2:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2.0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    tsv = run_pdftotext_tsv(args.pdf)
    result = {
        "source": args.pdf,
        "parser": "pdftotext-tsv",
        "has_text_layer": tsv is not None and bool(tsv.strip()),
        "num_pages": 0,
        "blocks": [], "sections": [], "tables": [],
        "figures": [], "equations": [], "references": [],
        "uncertainty": [],
    }
    if not result["has_text_layer"]:
        result["uncertainty"].append(
            "no text layer (pdftotext unavailable or empty); needs OCR/scanned-PDF path")
        if args.out == "-":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return 0

    pages = parse_tsv(tsv)
    result["num_pages"] = len(pages)
    parsed = assemble(pages)
    for k, v in parsed.items():
        result[k] = v

    if args.out == "-":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
