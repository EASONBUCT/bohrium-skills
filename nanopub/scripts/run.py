#!/usr/bin/env python3
"""nanopub single entry point.

Splits the paper's conclusions into individual, checkable assertions and binds
each to its minimal evidence (verbatim quote + source location) and provenance
(paper, authors, year, version), then exports a machine-readable nanopub
structure.

The script reads the real material and produces sentence-level assertions
deterministically; the agent may drop an optional /app/work/annotations.json
with finer S-P-O triples and confidence judgments, which the script merges.

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


def as_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("paragraphs", "items", "entries", "records", "sections"):
            if isinstance(x.get(k), list):
                return x[k]
    return []


def text_of(p):
    if isinstance(p, str):
        return p
    if not isinstance(p, dict):
        return ""
    for k in ("text", "content", "body", "paragraph", "para", "value"):
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


def load_paras(files, work_dir):
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
                txt = os.path.join(work_dir, "extracted.txt")
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


def split_sentences(text):
    # split on sentence boundaries, keeping citations/decimals intact
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


SPO_VERBS = ("are", "is", "were", "was", "have", "has", "shows", "show", "showed",
             "improves", "improve", "improved", "reduces", "reduce", "reduced",
             "uses", "use", "used", "achieves", "achieve", "achieved",
             "proposes", "propose", "proposed", "increases", "increase", "increased",
             "requires", "require", "required", "outperforms", "outperform",
             "outperformed", "demonstrates", "demonstrate", "demonstrated",
             "indicates", "indicate", "indicated")


def extract_spo(sentence):
    """Deterministic subject–predicate–object split on the first content verb."""
    s = sentence.strip().rstrip(".,;。，；")
    for verb in SPO_VERBS:
        m = re.search(r"\b" + verb + r"\b", s, re.I)
        if m:
            subj = s[:m.start()].strip(" -")
            obj = s[m.end():].strip(" -")
            if subj and obj:
                return subj, m.group(0), obj
    return "", "", s


def split_compound(text):
    """Split compound/coordinated sentences into finer assertions."""
    parts = re.split(r"\.\s+(?=[A-Z])|\;\s+|(?<=[a-z])\s+and\s+(?=[A-Z][a-z])", text)
    return [p.strip() for p in parts if len(p.strip()) > 8]


def paper_meta(files, case):
    m = _loadj(files.get("corpus-manifest.json", ""))
    if isinstance(m, list) and m and isinstance(m[0], dict):
        rec = m[0]
        return {"source_id": rec.get("doi") or rec.get("id") or "primary",
                "title": rec.get("title", ""), "authors": rec.get("authors", rec.get("author", "")),
                "year": rec.get("year", ""), "doi": rec.get("doi", ""),
                "license": rec.get("license", rec.get("licence", ""))}
    return {"source_id": case.get("case_id") or "primary",
            "title": case.get("title", ""), "authors": case.get("authors", ""),
            "year": case.get("year", ""), "doi": case.get("doi", "")}


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
    annotations = _loadj(os.path.join(args.work, "annotations.json")) or {}
    meta = paper_meta(files, case)

    paras = load_paras(files, args.work)

    nanopubs = []
    anno_triples = (annotations or {}).get("assertions", []) if isinstance(annotations, dict) else []
    used_anno = set()

    # Agent-provided fine-grained assertions first.
    for a in anno_triples:
        if not isinstance(a, dict):
            continue
        text = a.get("assertion") or a.get("text") or ""
        if not text:
            continue
        used_anno.add(text)
        nanopubs.append({
            "id": "np%d" % len(nanopubs),
            "assertion": {"subject": a.get("subject", ""),
                          "predicate": a.get("predicate", a.get("relation", "")),
                          "object": a.get("object", "")},
            "evidence": {"quote": a.get("evidence") or text,
                         "location": a.get("paragraph_id", a.get("location", ""))},
            "provenance": meta,
            "confidence": a.get("confidence", ""),
        })

    # Deterministic fallback: every (possibly compound) sentence is a candidate
    # assertion with a subject–predicate–object split.
    for p in paras:
        for s in split_sentences(p["text"]):
            for clause in split_compound(s):
                if clause in used_anno:
                    continue
                subj, pred, obj = extract_spo(clause)
                nanopubs.append({
                    "id": "np%d" % len(nanopubs),
                    "assertion": {"subject": subj, "predicate": pred, "object": obj,
                                  "text": clause},
                    "evidence": {"quote": clause, "location": p["paragraph_id"]},
                    "provenance": meta,
                    "confidence": "machine" if subj else "",
                })

    export = {
        "schema": "nanopub/v2",
        "provenance": meta,
        "nanopublications": nanopubs,
        "stats": {"assertions": len(nanopubs)},
    }
    with open(os.path.join(args.output, "nanopubs.json"), "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    result = dict(contract)
    result.update({
        "case_id": case.get("case_id"),
        "status": "complete" if nanopubs else "partial",
        "sources": {"provenance": meta, "assertions": len(nanopubs)},
        "uncertainty": [] if nanopubs else ["no paper material detected under input"],
        "change_log": ["split %d paragraphs into %d checkable assertions"
                       % (len(paras), len(nanopubs))],
        "nanopublications": nanopubs,
    })
    with open(os.path.join(args.output, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": result["status"], "paragraphs": len(paras),
                      "assertions": len(nanopubs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
