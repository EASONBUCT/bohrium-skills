#!/usr/bin/env python3
"""translate-paper single entry point.

Reads the source paper directly and produces a verifiable bilingual result:
segment paragraphs 1:1, extract a terminology table, merge the agent's
translations, and verify that numbers, units, citation markers, and figure/table
references are preserved. The script does all the deterministic work; the agent
only supplies the actual translations via /app/work/annotations.json.

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
        if fname.endswith(".json") and fname not in ("case.json", "corpus-manifest.json"):
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


def extract_terms(paras):
    """Deterministic terminology candidates: acronyms + repeated terms."""
    terms = {}
    all_text = " ".join(p["text"] for p in paras)
    for m in re.finditer(r"\b([A-Z][a-zA-Z\- ]{1,40}?)\s*\(([A-Z][A-Z0-9]{1,10})\)", all_text):
        acr = m.group(2)
        terms.setdefault(acr, {"source": acr, "target": "", "first_seen": ""})
    # repeated multi-word capitalized terms
    freq = {}
    for m in re.finditer(r"\b[A-Z][a-z]+(?:[ \-][A-Z][a-z]+){1,3}\b", all_text):
        t = m.group(0)
        freq[t] = freq.get(t, 0) + 1
    for t, c in freq.items():
        if c >= 2:
            terms.setdefault(t, {"source": t, "target": "", "first_seen": ""})
    return list(terms.values())


def find_first_seen(paras, term):
    for p in paras:
        if term.lower() in p["text"].lower():
            return p["paragraph_id"]
    return ""


def extract_tokens(text):
    """Numbers, units, citation markers, and figure/table refs to preserve."""
    toks = []
    for m in re.finditer(r"\d+(?:\.\d+)?\s*(?:%|nm|µm|°C|mm|kg|g|s|ms|mL|mol|Hz|GHz|m|cm)?", text):
        toks.append(m.group(0))
    for m in re.finditer(r"\[\d+(?:[-,]\d+)*\]", text):
        toks.append(m.group(0))
    for m in re.finditer(r"(?:Fig\.|Figure|Table|Tab\.)\s*\d+", text, re.I):
        toks.append(m.group(0))
    return toks


def verify_segment(source, translation):
    if not translation:
        return {"numbers_ok": None, "units_ok": None, "citations_ok": None}
    src_toks = extract_tokens(source)
    missing = [t for t in src_toks if t not in translation]
    return {"numbers_ok": not any(re.search(r"\d", t) for t in missing),
            "units_ok": not any(re.search(r"(nm|µm|°C|mm|kg|g|s|ms|mL|mol|Hz|GHz|m|cm|%)", t) for t in missing),
            "citations_ok": not any(re.search(r"\[|Fig|Figure|Table", t, re.I) for t in missing),
            "missing_tokens": missing}


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
    annotations = annotations if isinstance(annotations, dict) else {}

    source_lang = case.get("source_language") or annotations.get("source_language") or "en"
    target_lang = case.get("target_language") or annotations.get("target_language") or "zh"

    paras = load_paras(files, args.work)
    terms = extract_terms(paras)
    # lock agent terminology into the table
    anno_terms = annotations.get("terminology", []) or []
    term_by_src = {t["source"]: t for t in terms}
    for at in anno_terms:
        if isinstance(at, dict) and at.get("source"):
            term_by_src.setdefault(at["source"], at).update(at)
    for t in term_by_src.values():
        t.setdefault("target", "")
        if not t.get("first_seen"):
            t["first_seen"] = find_first_seen(paras, t["source"])

    # merge agent translations keyed by paragraph_id
    anno_trans = {}
    for tr in annotations.get("translations", []) or []:
        if isinstance(tr, dict) and tr.get("paragraph_id"):
            anno_trans[str(tr["paragraph_id"])] = tr.get("translation", "")

    segments, untranslated, verification = [], [], []
    for p in paras:
        translation = anno_trans.get(str(p["paragraph_id"]), "")
        segments.append({"para_id": p["paragraph_id"], "source": p["text"],
                         "translation": translation, "notes": ""})
        if not translation:
            untranslated.append(p["paragraph_id"])
        verification.append({"para_id": p["paragraph_id"],
                             **verify_segment(p["text"], translation)})

    export = {
        "schema": "translate-paper/v2",
        "source_language": source_lang,
        "target_language": target_lang,
        "terminology": list(term_by_src.values()),
        "segments": segments,
        "verification": verification,
        "untranslated_segments": untranslated,
        "stats": {"paragraphs": len(paras), "terms": len(term_by_src),
                  "translated": len(paras) - len(untranslated),
                  "untranslated": len(untranslated)},
    }
    with open(os.path.join(args.output, "translation.json"), "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    result = dict(contract)
    result.update({
        "case_id": case.get("case_id"),
        "status": "complete" if paras else "partial",
        "sources": {"paragraphs": len(paras), "terms": len(term_by_src)},
        "uncertainty": (["%d segments untranslated" % len(untranslated)] if untranslated else [])
                       + ([] if paras else ["no source material detected"]),
        "change_log": ["segmented %d paragraphs, extracted %d terms" % (len(paras), len(term_by_src)),
                       "%d/%d segments translated" % (len(paras) - len(untranslated), len(paras))],
        "terminology": list(term_by_src.values()),
        "segments": segments,
        "verification": verification,
        "untranslated_segments": untranslated,
    })
    with open(os.path.join(args.output, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": result["status"], "paragraphs": len(paras),
                      "terms": len(term_by_src), "translated": len(paras) - len(untranslated),
                      "untranslated": len(untranslated)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
