#!/usr/bin/env python3
"""Run queries against a built graph and return result subgraphs + evidence.

Queries (queries.json) is a list of objects; each supports:
  {"id","type":"neighbors","node":"<label>","rel":"uses"}
  {"id","type":"path","source":"<label>","target":"<label>"}
  {"id","type":"nodes_by_type","node_type":"conclusion"}

Matching is by node label (case-insensitive substring). A query with no match
returns an empty result honestly — never a fabricated match.

Usage:
  python query_graph.py --graph graph.json --queries queries.json \
      --out query-results.json
"""

import argparse
import json
import sys


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def find_nodes(graph, label=None, node_type=None):
    out = []
    for n in graph.get("nodes", []):
        if label and label.lower() not in (n.get("label") or "").lower():
            continue
        if node_type and n.get("type") != node_type:
            continue
        out.append(n)
    return out


def run_query(graph, q):
    qid = q.get("id", "q")
    qtype = q.get("type", "neighbors")
    if qtype == "neighbors":
        nodes = find_nodes(graph, label=q.get("node"))
        sub = {"nodes": nodes, "edges": []}
        ids = {n["id"] for n in nodes}
        for e in graph.get("edges", []):
            if e.get("source") in ids or e.get("target") in ids:
                if not q.get("rel") or e.get("type") == q.get("rel"):
                    sub["edges"].append(e)
        return {"id": qid, "query": q, "matches": len(nodes), "subgraph": sub,
                "evidence": [ev for e in sub["edges"] for ev in e.get("evidence", [])]}
    if qtype == "path":
        src = find_nodes(graph, label=q.get("source"))
        tgt = find_nodes(graph, label=q.get("target"))
        sid = {n["id"] for n in src}
        tid = {n["id"] for n in tgt}
        sub = {"nodes": src + tgt, "edges": []}
        for e in graph.get("edges", []):
            if (e.get("source") in sid and e.get("target") in tid) or \
               (e.get("source") in tid and e.get("target") in sid):
                sub["edges"].append(e)
        return {"id": qid, "query": q, "matches": len(sub["edges"]),
                "subgraph": sub,
                "evidence": [ev for e in sub["edges"] for ev in e.get("evidence", [])]}
    if qtype == "nodes_by_type":
        nodes = find_nodes(graph, node_type=q.get("node_type"))
        return {"id": qid, "query": q, "matches": len(nodes),
                "subgraph": {"nodes": nodes, "edges": []},
                "evidence": [m for n in nodes for m in n.get("mentions", [])]}
    return {"id": qid, "query": q, "matches": 0,
            "subgraph": {"nodes": [], "edges": []}, "evidence": [],
            "error": "unknown query type %r" % qtype}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    graph = load(args.graph)
    queries = load(args.queries)
    if isinstance(queries, dict):
        queries = queries.get("queries", [])

    results = [run_query(graph, q) for q in queries]

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"queries": results}, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "queries": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
