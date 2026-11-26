#!/usr/bin/env python3
"""Assemble an evidence-bound knowledge graph from an extraction JSON.

The agent writes extraction.json (entities with mentions, merge_groups,
relations with evidence, conflicts). This script is deterministic:
  - applies merge groups into canonical nodes (merged_from + justification)
  - assigns stable node/edge ids
  - binds evidence to nodes and edges
  - emits graph.json (nodes, edges, conflicts) per assets/graph.schema.json

Usage:
  python build_graph.py --extraction extraction.json \
      --manifest corpus-manifest.json --out graph.json
"""

import argparse
import json
import sys


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    ex = load(args.extraction)
    manifest = load(args.manifest) if args.manifest else {}

    entities = ex.get("entities", [])
    merge_groups = ex.get("merge_groups", []) or []
    relations = ex.get("relations", [])
    conflicts = ex.get("conflicts", [])

    # map entity id -> entity
    by_id = {}
    for e in entities:
        by_id[e.get("id")] = e

    # apply merge groups: first entity is canonical
    canonical_of = {}   # entity id -> canonical entity id
    for g in merge_groups:
        if not g:
            continue
        canon = g[0]
        for eid in g:
            canonical_of[eid] = canon

    # build nodes
    nodes = []
    node_id_of = {}     # entity id -> node id
    seen_canon = set()
    for e in entities:
        eid = e.get("id")
        canon = canonical_of.get(eid, eid)
        if canon in seen_canon:
            continue
        seen_canon.add(canon)
        canon_entity = by_id.get(canon, e)
        # collect all mentions from every entity merged into this canonical node
        mentions = list(canon_entity.get("mentions", []))
        merged_from = [x for x in (g for g in merge_groups if g and g[0] == canon) for x in g[1:]]
        for meid in merged_from:
            mentions.extend(by_id.get(meid, {}).get("mentions", []))
        node_id = canon
        node_id_of[canon] = node_id
        nodes.append({
            "id": node_id,
            "type": canon_entity.get("type"),
            "label": canon_entity.get("label"),
            "mentions": mentions,
            "merged_from": merged_from,
            "merge_justification": ex.get("merge_justifications", {}).get(canon, ""),
        })

    # map every entity id to its node id (for relation source/target resolution)
    for e in entities:
        eid = e.get("id")
        canon = canonical_of.get(eid, eid)
        node_id_of[eid] = node_id_of.get(canon, canon)

    # build edges
    edges = []
    for r in relations:
        rid = r.get("id") or ("r%d" % (len(edges) + 1))
        src = node_id_of.get(r.get("source"), r.get("source"))
        tgt = node_id_of.get(r.get("target"), r.get("target"))
        edges.append({
            "id": rid,
            "type": r.get("type"),
            "source": src,
            "target": tgt,
            "direction": r.get("direction", "%s->%s" % (src, tgt)),
            "condition": r.get("condition", ""),
            "evidence": r.get("evidence", []),
        })

    graph = {
        "schema": "kg-builder/v1",
        "corpus": {
            "sources": manifest.get("sources") or manifest.get("papers") or [],
            "note": "root DOI/title/authors belong to the first paper only",
        },
        "nodes": nodes,
        "edges": edges,
        "conflicts": conflicts,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "nodes": len(nodes),
                      "edges": len(edges), "conflicts": len(conflicts)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
