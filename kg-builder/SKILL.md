---
name: kg-builder
description: Build an evidence-bound knowledge graph from the papers under /input. Per the task's 输入修订 the material is JATS-style (corpus manifest, a paragraph index, and per-paper paragraph files); positions are JATS paragraph IDs, not PDF pages. The script reads the real files, builds nodes and edges with an independent source_id + paragraph_id + verbatim quote on every node/edge, runs at least 3 evidence-backed queries, records cross-paper merge justifications and conflicts, and writes result.json echoing the task.md output_contract fields under /app/output. Use when a case provides two papers and asks for entity/relation extraction, evidence binding, or graph queries. Do not use for slides or reference renumbering.
---

# Papers → evidence-bound knowledge graph

One command builds the graph. The script reads the real JATS-style files itself;
you (the agent) supply richer entity/relation semantics via `annotations.json`,
which the script evidence-binds and merges.

## Procedure (minimal)

1. Read `/input/case.json` and `/input/task.md` for `case_id`, the
   `output_contract` fields, and the exact input files. The task states the
   material: `corpus-manifest.json`, `material.json`, `primary-material.json`,
   `secondary-material.json`, `secondary-publisher.xml`.
2. Read the paragraph texts to understand the two papers.
3. (Optional) Write `/app/work/annotations.json` with `nodes` (label, type,
   source_id, paragraph_id, quote), `relations` (source/target labels, type,
   direction, condition, evidence), and `merges` / `conflicts` for cross-paper
   same-concept decisions.
4. Run:
   ```
   python scripts/run.py --input /input --work /app/work --output /app/output
   ```
5. Confirm `/app/output/graph.json` and `/app/output/result.json` exist, with
   every node/edge carrying `source_id` + `paragraph_id` + `quote`, and at least
   3 queries with evidence.

## What run.py does (deterministic, verifiable)

- Reads the corpus manifest and the paragraph index / per-paper files.
- Ensures every node and edge has an independent `source_id`, `paragraph_id`,
  and a verbatim quote from the paragraph text.
- Provides a deterministic term/acronym fallback so the graph is never empty,
  and co-occurrence edges bound to the same paragraph.
- Runs ≥3 queries (per-paper inventory, neighbours of the hub, cross-paper
  shared terms) with result subgraphs and evidence.
- Writes `graph.json` and `result.json` (contract + status/sources/uncertainty/
  change_log). Does not merge different objects just because a term matches;
  `merges` and `conflicts` are recorded separately.

## annotations.json (optional, illustrative)

```json
{"nodes":[{"label":"Transformer","type":"method","source_id":"10.1/p1","paragraph_id":"p1-1","quote":"..."}],
 "relations":[{"source":"Transformer","target":"sequence learning","type":"used_for","direction":"forward","source_id":"10.1/p1","paragraph_id":"p1-1","quote":"..."}],
 "merges":[{"term":"TF","canonical":"Transformer","reason":"acronym expansion","source_id":"10.1/p1"}],
 "conflicts":[{"term":"Transformer","reason":"different model instance in paper 2"}]}
```

## Output under /app/output

- `graph.json` — papers, nodes, edges, queries, merges, conflicts, stats.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources`
  + `uncertainty` + `change_log` + `nodes` + `edges` + `queries`.

## Failure handling

- No paragraph material → `status: partial`, flagged. Full tree in
  `references/exception-handling.md`. Never invent a PDF page number: the
  position is the JATS `paragraph_id`.

## Resources

- `references/entity-relation-schema.md`, `references/alignment-rules.md`,
  `references/exception-handling.md`
- `assets/graph.schema.json`
- `scripts/run.py`
