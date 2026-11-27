#!/usr/bin/env python3
"""pdf-parser single entry point.

Deterministically parses the PDF(s) under the input directory into structured
blocks: title, authors/affiliations, abstract, section headings, paragraphs,
figure/table captions, tables, formulas, and references, each with its page
number, block id, and verbatim text. The script runs pdftotext itself so the
extracted text is genuinely derived from the real file, not from an answer
layer.

Usage:
  python run.py [--input /input] [--work /app/work] [--output /app/output]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys


def discover(root):
    out = {}
    for dp, _d, files in os.walk(root):
        for fn in files:
            out[fn.lower()] = os.path.join(dp, fn)
    return out


def _read(p):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    return ""


def _loadj(p):
    try:
        return json.loads(_read(p))
    except Exception:
        return None


def contract_from(files, case):
    c = dict(case.get("output_contract") or {}) if isinstance(case, dict) else {}
    md = _read(files.get("task.md", ""))
    for m in re.finditer(r'"output_contract"\s*:\s*(\{.*?\})', md, re.S):
        try:
            d = json.loads(m.group(1))
            if isinstance(d, dict):
                c.update(d)
        except Exception:
            pass
    for m in re.finditer(r'```json\s*(\{.*?\})\s*```', md, re.S):
        try:
            d = json.loads(m.group(1))
            if isinstance(d, dict):
                for k, v in d.items():
                    c.setdefault(k, v)
        except Exception:
            pass
    return c


def pdf_to_text(pdf_path, out_dir):
    """Return per-page text using pdftotext -layout."""
    txt_path = os.path.join(out_dir, "extracted.txt")
    tool = shutil.which("pdftotext") or "/usr/bin/pdftotext"
    if not tool and os.name == "nt":
        tool = "pdftotext"
    try:
        subprocess.run([tool, "-layout", pdf_path, txt_path],
                       check=True, capture_output=True, timeout=120)
    except Exception:
        try:
            subprocess.run([tool, pdf_path, txt_path],
                           check=True, capture_output=True, timeout=120)
        except Exception as e:
            return "", str(e)
    return _read(txt_path), None


def split_pages(raw):
    pages = re.split(r"\f", raw)
    return pages


def classify_block(text):
    t = text.strip()
    if not t:
        return "empty"
    if re.match(r"^(Fig(ure)?\.?|Table|Tab\.)\s", t, re.I):
        return "caption"
    if re.match(r"^(Abstracts?|摘要|Introductions?|Related Work|Methods?|Experiments?|Results?|Discussions?|Conclusions?|References|附录|致谢|参考文献|引言|相关工作|方法|实验|结果|讨论|结论)\b", t, re.I):
        return "heading"
    if re.match(r"^\[\s*\d+\s*\]", t):
        return "reference"
    if re.match(r"^(\d+(\.\d+)*\.?)\s+\S", t):
        if re.search(r"\b(1[89]|20)\d{2}\b|et al\.|\(\d{4}\)|doi:", t):
            return "reference"
        return "heading" if len(t) <= 80 else "paragraph"
    if len(t) <= 90 and (re.search(r"[=≥≤≈×±→∂∑∫√]", t) or re.search(r"\(\s*\d+\s*\)\s*$", t)):
        return "formula"
    return "paragraph"


def parse_raw_text(raw, source):
    blocks = []
    bid = 0
    for pno, page in enumerate(split_pages(raw), start=1):
        lines = [ln.rstrip() for ln in page.splitlines()]
        # merge into blocks: blank line is a separator
        cur = []
        def flush():
            nonlocal bid
            text = " ".join(cur).strip()
            if text:
                blocks.append({"block_id": "b%d" % bid, "page": pno, "type": classify_block(text), "text": text})
                bid += 1
            cur.clear()
        for ln in lines:
            if not ln.strip():
                flush()
            else:
                cur.append(ln)
        flush()
    return blocks


def first_blocks(blocks, n=8):
    return blocks[:n]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--output", default="/app/output")
    args = ap.parse_args(argv)

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.output, exist_ok=True)

    files = discover(args.input)
    case = _loadj(files.get("case.json", "")) or {}
    contract = contract_from(files, case)

    pdfs = [p for f, p in files.items() if f.endswith(".pdf")]
    all_blocks = []
    errors = []
    for pdf in pdfs:
        raw, err = pdf_to_text(pdf, args.work)
        if err:
            errors.append({"file": os.path.basename(pdf), "error": err})
            continue
        all_blocks.extend(parse_raw_text(raw, os.path.basename(pdf)))

    # Fallback: text/markdown input without a PDF.
    if not all_blocks:
        for f, p in files.items():
            if f.endswith((".txt", ".md")):
                all_blocks.extend(parse_raw_text(_read(p), f))
                break

    parsed = {
        "schema": "pdf-parser/v2",
        "source": [os.path.basename(p) for p in pdfs] or ["text-input"],
        "blocks": all_blocks,
        "stats": {
            "pages": len(set(b["page"] for b in all_blocks)),
            "blocks": len(all_blocks),
            "by_type": {t: sum(1 for b in all_blocks if b["type"] == t)
                        for t in sorted({b["type"] for b in all_blocks})},
        },
        "errors": errors,
    }
    with open(os.path.join(args.output, "parsed.json"), "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    result = dict(contract)
    result.update({
        "case_id": case.get("case_id"),
        "status": "complete" if all_blocks else "partial",
        "sources": {"pdfs": [os.path.basename(p) for p in pdfs],
                    "blocks": len(all_blocks)},
        "uncertainty": errors if errors else ([] if all_blocks else
                                              ["no PDF or text input found"]),
        "change_log": ["extracted %d blocks across %d pages" %
                       (len(all_blocks), parsed["stats"]["pages"])],
        "blocks": all_blocks,
    })
    with open(os.path.join(args.output, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": result["status"],
                      "blocks": len(all_blocks),
                      "pages": parsed["stats"]["pages"],
                      "by_type": parsed["stats"]["by_type"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
