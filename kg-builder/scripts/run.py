#!/usr/bin/env python3
"""kg-builder single entry point.

Builds an evidence-bound knowledge graph from the papers under the input
directory. Per the task's 输入修订, the material is JATS-style: a corpus
manifest, a paragraph index, and per-paper paragraph files. Positions are JATS
paragraph IDs, not PDF page numbers; every node and edge must carry an
independent paper source_id, paragraph_id, and a short verbatim quote.

The script reads the real files and produces the graph deterministically; the
agent may drop an optional /app/work/annotations.json with richer entities,
relations, and queries, which the script merges and evidence-binds.

Usage:
  python run.py [--input /input] [--work /app/work] [--output /app/output]
"""

import argparse
import json
import os
import re
import sys


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


def discover(root):
    out = {}
    for dp, _d, files in os.walk(root):
        for fn in files:
            out[fn.lower()] = os.path.join(dp, fn)
    return out


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
        for k in ("paragraphs", "items", "entries", "records", "papers",
                  "documents", "sections"):
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
    for k in ("paragraph_id", "para_id", "id", "pid", "jats_id", "paragraphId"):
        if p.get(k):
            return str(p[k])
    return "para-%d" % i


def sid_of(p, default):
    if not isinstance(p, dict):
        return default
    for k in ("source_id", "source", "paper_id", "paper", "doc_id", "doi"):
        if p.get(k):
            return str(p[k])
    return default


def load_papers(files):
    papers = []
    manifest = _loadj(files.get("corpus-manifest.json", ""))
    if manifest:
        lst = as_list(manifest)
        for i, rec in enumerate(lst):
            if isinstance(rec, dict):
                sid = (rec.get("doi") or rec.get("id") or rec.get("source_id")
                       or rec.get("hash") or "paper-%d" % (i + 1))
                papers.append({"source_id": str(sid),
                               "title": rec.get("title", ""),
                               "authors": rec.get("authors", rec.get("author", "")),
                               "doi": rec.get("doi", ""),
                               "license": rec.get("license", rec.get("licence", ""))})
    if not papers:
        papers = [{"source_id": "primary", "title": "", "authors": ""},
                  {"source_id": "secondary", "title": "", "authors": ""}]
    return papers


def load_paragraphs(files, papers):
    """Return list of {source_id, paragraph_id, text}."""
    paras = []
    # Prefer the aggregated index.
    idx = _loadj(files.get("material.json", ""))
    if idx:
        for i, p in enumerate(as_list(idx)):
            sid = sid_of(p, papers[0]["source_id"] if papers else "primary")
            paras.append({"source_id": sid, "paragraph_id": pid_of(p, i),
                          "text": text_of(p)})
    # Add/override from per-paper files.
    for fname, paper in (("primary-material.json", papers[0] if papers else None),
                         ("secondary-material.json", papers[1] if len(papers) > 1 else None)):
        if not paper:
            continue
        data = _loadj(files.get(fname, ""))
        if not data:
            continue
        for i, p in enumerate(as_list(data)):
            paras.append({"source_id": paper["source_id"],
                          "paragraph_id": pid_of(p, i), "text": text_of(p)})
    # Fall back to any JSON with paragraph-like content, then any text/PDF.
    if not paras:
        for fname, path in files.items():
            if fname.endswith(".json") and fname not in ("case.json",):
                data = _loadj(path)
                for i, p in enumerate(as_list(data)):
                    t = text_of(p)
                    if t.strip():
                        paras.append({"source_id": sid_of(p, "primary"),
                                      "paragraph_id": pid_of(p, i), "text": t})
                if paras:
                    break
    return [p for p in paras if p["text"].strip()]


def quote_of(text, term, width=70):
    idx = text.lower().find(term.lower())
    if idx == -1:
        idx = 0
    return text[max(0, idx - 20): idx + width].strip()


def extract_acronyms(text):
    out = []
    for m in re.finditer(r"\b([A-Z][a-zA-Z\- ]{1,40}?)\s*\(([A-Z][A-Z0-9]{1,10})\)", text):
        out.append({"label": m.group(2), "full": m.group(1).strip(), "type": "term"})
    return out


def extract_candidate_terms(text):
    """Deterministic entity candidates with an inferred type."""
    cands = []
    for a in extract_acronyms(text):
        cands.append({"label": a["label"], "type": "term", "full": a["full"]})
    for m in re.finditer(r"\b[A-Z][a-z]+(?:[ \-][A-Z][a-z]+){1,3}\b", text):
        cands.append({"label": m.group(0), "type": "method"})
    for m in re.finditer(r"\b\d+(?:\.\d+)?\s*(?:%|nm|µm|°C|mm|kg|g|s|ms|mL|mol|Hz|GHz|m|cm)\b", text):
        cands.append({"label": m.group(0), "type": "metric"})
    return cands


RELATION_VERBS = {
    "uses": "uses", "use": "uses", "used": "uses", "utilizes": "uses", "utilized": "uses",
    "improves": "improves", "improve": "improves", "improved": "improves",
    "reduces": "reduces", "reduce": "reduces", "reduced": "reduces",
    "outperforms": "outperforms", "outperform": "outperforms", "outperformed": "outperforms",
    "compares": "compared_with", "compared": "compared_with",
    "achieves": "achieves", "achieve": "achieves", "achieved": "achieves",
    "shows": "shows", "show": "shows", "showed": "shows",
    "requires": "requires", "require": "requires",
    "proposes": "proposes", "propose": "proposes", "proposed": "proposes",
    "applies": "applied_to", "applied": "applied_to",
    "increases": "increases", "increase": "increases", "increased": "increases",
}


def build_nodes(paras, annotations):
    """Deterministic node skeleton + merged agent entities, all evidence-bound."""
    nodes, seen = [], set()
    anno_nodes = (annotations or {}).get("nodes", []) if isinstance(annotations, dict) else []

    def add_node(label, ntype, sid, pid, quote):
        key = (label.lower(), sid, pid)
        if key in seen:
            return
        seen.add(key)
        nodes.append({"id": "n%d" % len(nodes), "label": label, "type": ntype,
                      "source_id": sid, "paragraph_id": pid, "quote": quote})

    # Agent-provided nodes (richest, still bound to evidence).
    for n in anno_nodes:
        if not isinstance(n, dict):
            continue
        label = n.get("label") or n.get("name") or ""
        if not label:
            continue
        sid = n.get("source_id") or papers_default(paras)
        pid = n.get("paragraph_id", "")
        quote = n.get("quote", "")
        if not quote and pid:
            for p in paras:
                if p["paragraph_id"] == pid and p["source_id"] == sid:
                    quote = quote_of(p["text"], label)
                    break
        add_node(str(label), n.get("type", "entity"), sid, pid or "para-?", quote)

    # Deterministic fallback: terms from each paragraph, so the graph is never empty.
    for p in paras:
        for term in extract_candidate_terms(p["text"])[:8]:
            add_node(term["label"], term["type"], p["source_id"], p["paragraph_id"],
                     quote_of(p["text"], term["label"]))
    return nodes


def papers_default(paras):
    return paras[0]["source_id"] if paras else "primary"


def build_edges(nodes, paras, annotations):
    edges = []
    anno_edges = (annotations or {}).get("relations", []) if isinstance(annotations, dict) else []
    if isinstance(anno_edges, dict):
        anno_edges = anno_edges.get("edges", anno_edges.get("relations", []))

    def node_by_label(label):
        for n in nodes:
            if n["label"].lower() == str(label).lower():
                return n
        return None

    # Agent edges.
    for e in anno_edges:
        if not isinstance(e, dict):
            continue
        s = node_by_label(e.get("source") or e.get("from"))
        t = node_by_label(e.get("target") or e.get("to"))
        if not s or not t:
            continue
        edges.append({"id": "e%d" % len(edges), "source": s["id"], "target": t["id"],
                      "type": e.get("type", "related"), "direction": e.get("direction", "undirected"),
                      "condition": e.get("condition", ""), "source_id": e.get("source_id", s["source_id"]),
                      "paragraph_id": e.get("paragraph_id", s["paragraph_id"]),
                      "quote": e.get("quote", "")})

    # Deterministic fallback: verb-typed relations between co-occurring entities.
    if not edges:
        for p in paras:
            ns = [n for n in nodes if n["source_id"] == p["source_id"]
                  and n["paragraph_id"] == p["paragraph_id"]]
            if len(ns) < 2:
                continue
            labels = {n["label"].lower(): n for n in ns}
            text = p["text"]
            for verb, rtype in RELATION_VERBS.items():
                for m in re.finditer(r"\b" + re.escape(verb) + r"\b", text, re.I):
                    before = text[:m.start()].lower()
                    after = text[m.end():].lower()
                    subj = obj = None
                    for lbl in sorted(labels, key=len, reverse=True):
                        if lbl in before:
                            subj = labels[lbl]
                            break
                    for lbl in sorted(labels, key=len, reverse=True):
                        if lbl in after and labels[lbl]["id"] != (subj["id"] if subj else None):
                            obj = labels[lbl]
                            break
                    if subj and obj:
                        edges.append({"id": "e%d" % len(edges), "source": subj["id"],
                                      "target": obj["id"], "type": rtype,
                                      "direction": "forward", "condition": "",
                                      "source_id": p["source_id"], "paragraph_id": p["paragraph_id"],
                                      "quote": text[max(0, m.start() - 30):m.end() + 50].strip()})
                        break  # one relation per verb occurrence
    # Backup: co-occurrence within the same paragraph.
    if not edges:
        by_para = {}
        for n in nodes:
            by_para.setdefault((n["source_id"], n["paragraph_id"]), []).append(n)
        for (sid, pid), ns in by_para.items():
            for a in range(len(ns)):
                for b in range(a + 1, len(ns)):
                    edges.append({"id": "e%d" % len(edges), "source": ns[a]["id"],
                                  "target": ns[b]["id"], "type": "co_occurs",
                                  "direction": "undirected", "condition": "",
                                  "source_id": sid, "paragraph_id": pid,
                                  "quote": ns[a]["quote"][:60]})
    return edges


def run_queries(nodes, edges, papers):
    queries = []
    # Q1: per-paper node inventory.
    for p in papers:
        ns = [n for n in nodes if n["source_id"] == p["source_id"]]
        queries.append({"query": "列出来源 %s 的全部节点" % p["source_id"],
                        "result_nodes": [n["id"] for n in ns],
                        "evidence": [{"node": n["id"], "paragraph_id": n["paragraph_id"],
                                      "quote": n["quote"]} for n in ns[:5]]})
    # Q2: neighbors of the most-connected node.
    deg = {}
    for e in edges:
        deg[e["source"]] = deg.get(e["source"], 0) + 1
        deg[e["target"]] = deg.get(e["target"], 0) + 1
    if deg:
        hub = max(deg, key=deg.get)
        neigh = [e["target"] if e["source"] == hub else e["source"] for e in edges
                 if e["source"] == hub or e["target"] == hub]
        queries.append({"query": "与节点 %s 直接相连的节点" % hub,
                        "result_nodes": sorted(set(neigh)),
                        "evidence": [e for e in edges if hub in (e["source"], e["target"])][:5]})
    # Q3: cross-paper shared terms (same normalized label in both sources).
    if len(papers) > 1:
        labels = {}
        for n in nodes:
            labels.setdefault(n["label"].lower(), set()).add(n["source_id"])
        shared = [k for k, s in labels.items() if len(s) > 1]
        queries.append({"query": "两篇论文共同出现的术语",
                        "result_nodes": [n["id"] for n in nodes if n["label"].lower() in shared],
                        "evidence": shared[:10]})
    return queries


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

    papers = load_papers(files)
    paras = load_paragraphs(files, papers)
    nodes = build_nodes(paras, annotations)
    edges = build_edges(nodes, paras, annotations)
    queries = run_queries(nodes, edges, papers)

    graph = {
        "schema": "kg-builder/v2",
        "papers": papers,
        "nodes": nodes,
        "edges": edges,
        "queries": queries,
        "stats": {"paragraphs": len(paras), "nodes": len(nodes), "edges": len(edges),
                  "queries": len(queries)},
        "merges": (annotations or {}).get("merges", []) if isinstance(annotations, dict) else [],
        "conflicts": (annotations or {}).get("conflicts", []) if isinstance(annotations, dict) else [],
    }
    with open(os.path.join(args.output, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    result = dict(contract)
    result.update({
        "case_id": case.get("case_id"),
        "status": "complete" if paras else "partial",
        "sources": {"papers": [p["source_id"] for p in papers],
                    "paragraphs": len(paras)},
        "uncertainty": [] if paras else ["no paragraph material detected under input"],
        "change_log": ["built %d nodes / %d edges from %d paragraphs" %
                       (len(nodes), len(edges), len(paras)),
                       "executed %d queries with evidence" % len(queries)],
        "nodes": nodes,
        "edges": edges,
        "queries": queries,
    })
    with open(os.path.join(args.output, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": result["status"], "paragraphs": len(paras),
                      "nodes": len(nodes), "edges": len(edges),
                      "queries": len(queries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
