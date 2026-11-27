#!/usr/bin/env python3
"""note-builder single entry point.

Turns a paper (PDF or paragraph-indexed JSON/text) into structured notes: a
paper card with the five core fields (research question, data, method, main
findings, limitations) plus per-section notes, every note anchored back to its
source location (paragraph id / page) with a verbatim quote.

The script reads the real material and produces the notes deterministically;
the agent may drop an optional /app/work/annotations.json with richer summaries,
which the script merges and anchors.

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


HEAD_RE = re.compile(
    r"^(Abstracts?|摘要|Introductions?|Related Work|Methods?|Experiments?|Results?|Discussions?|Conclusions?|References|附录|致谢|参考文献|引言|相关工作|方法|实验|结果|讨论|结论)\b|^\d+(\.\d+)*\.?\s+\S",
    re.I)


def as_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("paragraphs", "items", "entries", "records", "sections", "documents"):
            if isinstance(x.get(k), list):
                return x[k]
    return []


def text_of(p):
    if isinstance(p, str):
        return p
    if not isinstance(p, dict):
        return ""
    for k in ("text", "content", "body", "paragraph", "para", "value", "title"):
        if isinstance(p.get(k), str):
            return p[k]
    return ""


def pid_of(p, i):
    if not isinstance(p, dict):
        return "para-%d" % i
    for k in ("paragraph_id", "para_id", "id", "pid", "paragraphId"):
        if p.get(k):
            return str(p[k])
    return "para-%d" % i


def load_paragraphs(files):
    paras = []
    for fname, path in files.items():
        if fname.endswith(".json") and fname != "case.json":
            data = _loadj(path)
            for i, p in enumerate(as_list(data)):
                t = text_of(p)
                if t.strip():
                    paras.append({"paragraph_id": pid_of(p, i), "text": t})
            if paras:
                break
    if not paras:
        for fname, path in files.items():
            if fname.endswith(".pdf"):
                tool = shutil.which("pdftotext") or "pdftotext"
                txt = os.path.join(args_out_tmp(), "extracted.txt")
                try:
                    subprocess.run([tool, "-layout", path, txt], check=True,
                                   capture_output=True, timeout=120)
                    raw = _read(txt)
                except Exception:
                    raw = ""
                for i, blk in enumerate(re.split(r"\n\s*\n", raw)):
                    if blk.strip():
                        paras.append({"paragraph_id": "p%d" % i, "text": blk.strip()})
                break
    if not paras:
        for fname, path in files.items():
            if fname.endswith((".txt", ".md")):
                raw = _read(path)
                for i, blk in enumerate(re.split(r"\n\s*\n", raw)):
                    if blk.strip():
                        paras.append({"paragraph_id": "p%d" % i, "text": blk.strip()})
                break
    return paras


def args_out_tmp():
    return os.environ.get("WORK_TMP", "/tmp")


def split_sections(paras):
    """Group paragraphs into sections by heading."""
    sections = []
    cur = None
    for p in paras:
        if HEAD_RE.match(p["text"].strip()):
            if cur:
                sections.append(cur)
            cur = {"section": p["text"].strip(), "paragraphs": [p]}
        else:
            if cur is None:
                cur = {"section": "(front)", "paragraphs": []}
            cur["paragraphs"].append(p)
    if cur:
        sections.append(cur)
    return sections


def key_items(text):
    """Deterministic extraction of citable anchors: numbers, terms, citations."""
    items = []
    for m in re.finditer(r"\[\d+(?:[-,]\d+)*\]", text):
        items.append(m.group(0))
    for m in re.finditer(r"\b\d+(?:\.\d+)?\s*(?:%|nm|°C|mm|kg|s|ms|mL|mol|Hz|GHz)\b", text):
        items.append(m.group(0))
    return items[:12]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--output", default="/app/output")
    args = ap.parse_args(argv)

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.output, exist_ok=True)
    os.environ["WORK_TMP"] = args.work

    files = discover(args.input)
    case = _loadj(files.get("case.json", "")) or {}
    contract = contract_from(files, case)
    annotations = _loadj(os.path.join(args.work, "annotations.json")) or {}

    paras = load_paragraphs(files)
    sections = split_sections(paras)

    # Paper card: five fields, each anchored.
    field_anchor = {}
    for sec in sections:
        name = sec["section"].lower()
        if "abstract" in name or "摘要" in name:
            field_anchor.setdefault("research_question", sec["paragraphs"][0] if sec["paragraphs"] else None)
        elif "method" in name or "方法" in name:
            field_anchor.setdefault("method", sec["paragraphs"][0] if sec["paragraphs"] else None)
        elif "result" in name or "结果" in name:
            field_anchor.setdefault("findings", sec["paragraphs"][0] if sec["paragraphs"] else None)
        elif "discussion" in name or "conclusion" in name or "结论" in name:
            field_anchor.setdefault("limitations", sec["paragraphs"][0] if sec["paragraphs"] else None)

    def field_note(fname, label):
        p = field_anchor.get(fname)
        if not p:
            return {"field": label, "text": "", "anchor": None, "quote": "",
                    "uncertain": True}
        return {"field": label, "text": p["text"], "anchor": p["paragraph_id"],
                "quote": p["text"][:120], "uncertain": False}

    card = {
        "research_question": field_note("research_question", "研究问题"),
        "data": field_note(None, "数据"),
        "method": field_note("method", "方法"),
        "findings": field_note("findings", "主要发现"),
        "limitations": field_note("limitations", "局限"),
    }
    # data: find numbers/units in methods/results as a deterministic fallback
    data_quote = ""
    data_anchor = None
    for sec in sections:
        for p in sec["paragraphs"]:
            if re.search(r"\b\d+(?:\.\d+)?\s*(?:%|nm|°C|mm|kg|s|ms|mL|mol|Hz|GHz)\b", p["text"]):
                data_quote = p["text"][:120]
                data_anchor = p["paragraph_id"]
                break
        if data_anchor:
            break
    card["data"] = {"field": "数据", "text": data_quote, "anchor": data_anchor,
                    "quote": data_quote, "uncertain": not bool(data_anchor)}

    section_notes = []
    for sec in sections:
        body = " ".join(p["text"] for p in sec["paragraphs"])
        section_notes.append({
            "section": sec["section"],
            "summary": body[:300],
            "anchor": sec["paragraphs"][0]["paragraph_id"] if sec["paragraphs"] else None,
            "key_items": key_items(body),
            "uncertain": False,
        })

    # Merge agent summaries if provided.
    anno = annotations if isinstance(annotations, dict) else {}
    for sn, extra in zip(section_notes, anno.get("section_summaries", []) or []):
        if isinstance(extra, dict) and extra.get("summary"):
            sn["summary"] = extra["summary"]
    for fname, extra in (anno.get("card") or {}).items():
        if fname in card and isinstance(extra, dict) and extra.get("text"):
            card[fname].update(extra)

    notes = {
        "schema": "note-builder/v2",
        "paper_card": card,
        "sections": section_notes,
        "stats": {"paragraphs": len(paras), "sections": len(section_notes)},
    }
    with open(os.path.join(args.output, "notes.json"), "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    result = dict(contract)
    result.update({
        "case_id": case.get("case_id"),
        "status": "complete" if paras else "partial",
        "sources": {"paragraphs": len(paras), "sections": len(section_notes)},
        "uncertainty": [] if paras else ["no paper material detected under input"],
        "change_log": ["built %d sections and a 5-field paper card from %d paragraphs"
                       % (len(section_notes), len(paras))],
        "paper_card": card,
        "sections": section_notes,
    })
    with open(os.path.join(args.output, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": result["status"], "paragraphs": len(paras),
                      "sections": len(section_notes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
