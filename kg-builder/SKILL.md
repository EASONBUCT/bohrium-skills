---
name: kg-builder
description: Build a queryable, evidence-bound knowledge graph from two (or more) paragraph-indexed research papers: typed entities (researcher/material/method/task/metric/conclusion), typed directed relations (uses/compares/outperforms/supports/contradicts/...), cross-paper entity alignment with merge justification and kept conflicts, and at least three executed queries with result subgraphs and verbatim evidence. Use when a case provides a corpus manifest plus paragraph-indexed material JSON under /input and asks for knowledge-graph construction whose result.json must echo the task.md output_contract fields under /app/output. Do not use for slides, prose polishing, or single-paper PDF text extraction.
---

# Literature → Evidence-bound Knowledge Graph

Turn a corpus of paragraph-indexed papers into one queryable graph whose every node and edge points back to a specific paper (`source_id`), paragraph (`paragraph_id`), and verbatim quote. The graph records what the papers actually say — never what a model would infer from common sense or a shared generic term.

## Runtime contract (authoritative)

- Read the real inputs under `/input`. The corpus manifest lists each paper's DOI/authors/hash/license; the material files carry paragraph-indexed body text. Root DOI/title/authors belong to the **first** paper only.
- Positions are **JATS paragraph ids**, not PDF pages. Never invent a page number.
- Work in `/app/work`. Final artifacts under `/app/output`, including `result.json` with every original `output_contract` field from `task.md`, plus `case_id`, `status`, `sources`, `uncertainty`, `change_log`.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial results early.
- Do not invent scores, logs, or paper content. A partial graph names its limits.

## Inputs to collect first

1. `/input/case.json` + `/input/task.md` — `case_id`, the `output_contract` fields.
2. `/input/corpus-manifest.json` — two papers: DOI, title, authors, source hash, license. First entry = `primary`, second = `secondary`.
3. `/input/material.json` — paragraph index of both papers.
4. `/input/primary-material.json`, `/input/secondary-material.json` — paragraph-indexed body text (fields like `paragraph_id`, `text`).
5. `/input/secondary-publisher.xml` (if present) — original XML for checking linearized inline formulas; do not infer values from it.

## Procedure (in order)

### 1. Read the corpus
Record the two `source_id`s (`primary`, `secondary`) and their DOIs/titles/authors from the manifest. Confirm the root metadata belongs to the first paper. Record `output_contract` fields.

### 2. Extract entities
For each paper, extract typed entities with verbatim surface forms and locations. Types and rules in `references/entity-relation-schema.md`. Headlines:
- Only entities that actually appear in the paper; no background/common-sense concepts.
- Keep the surface form verbatim (including linearized sub/superscripts); never reword.
- Record `source_id`, `paragraph_id`, and a short verbatim quote for every mention.
- Distinguish the authors' own claim from their report of others' work.

### 3. Extract relations
Only relations with direct textual support. Types, direction, and condition rules in `references/entity-relation-schema.md`. Headlines:
- Record type, direction, and the condition under which the relation holds (e.g. "at 300 K").
- Evidence strength: `direct` (stated) vs `inferred` (clearly implied). **Co-occurrence, review paraphrase, and speculation are NOT evidence** — drop them or mark `strength: none` and exclude from the graph.
- A relation may not combine the two papers' conditions, samples, or numbers into one claim.

### 4. Align entities across papers
- Merge only when there is positive evidence the two mentions refer to the same concept (same entity, or an alias/abbreviation resolved). Record `merged_from` and `merge_justification`.
- **Do not merge** when a generic term coincides but the physical sample / model instance / dataset / condition differs. Record these as `conflicts` (kind: `same-name-different-object`) with the reason.
- Same-paper multi-format (e.g. the paper appearing as both JSON and Markdown) is NOT cross-paper evidence.
- Rules in `references/alignment-rules.md`.

### 5. Build the graph
```
python scripts/build_graph.py --extraction /app/work/extraction.json \
  --manifest /input/corpus-manifest.json --out /app/work/graph.json
```
The script assigns stable node/edge ids, applies merge groups, binds evidence, and emits `nodes`, `edges`, `conflicts` (see `assets/graph.schema.json`). The `extraction.json` is written by you (the agent) following that schema; the script is deterministic.

### 6. Generate and run queries
```
python scripts/query_graph.py --graph /app/work/graph.json \
  --queries /app/work/queries.json --out /app/work/query-results.json
```
Provide at least 3 queries in `queries.json` (pattern + target). Each result returns the matching subgraph plus the supporting evidence. Example query patterns: "which methods were applied to material X", "does paper A outperform paper B on metric Y", "what conclusions are stated for task Z".

### 7. Assemble result.json
```
python scripts/write_result.py --graph /app/work/graph.json \
  --case /input/case.json --out /app/output/result.json \
  --output-contract '{"<field>":"<value>",...}' --status complete
```

## Output layout under /app/output

- `graph.json` — nodes, edges, conflicts, each with `source_id` + `paragraph_id` + quote evidence.
- `query-results.json` — ≥ 3 executed queries, their result subgraphs and evidence.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log`.

## Definition of done (check each before writing result.json)

- [ ] Every node/edge traces to a real `source_id` + `paragraph_id` + verbatim quote.
- [ ] Entities actually appear in the papers; no fabricated background concepts.
- [ ] Relations have type, direction, condition, and `direct`/`inferred` strength; no co-occurrence counted as evidence.
- [ ] Cross-paper merges carry `merged_from` + justification; kept conflicts are recorded, not forced.
- [ ] At least 3 queries are actually executed with result subgraphs + evidence.
- [ ] Root metadata is not misapplied to the second paper; no fake PDF page numbers.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full tree in `references/exception-handling.md`. Headlines:
- Missing/empty paper text → partial graph from what exists; never invent.
- Alias ambiguity → keep separate nodes and record a conflict, do not guess-merge.
- Conflicting relations → keep both, mark `uncertainty: "conflict"`.
- Query returns nothing → report the empty result honestly with the query, do not invent matches.
- Linearized formulas → quote them verbatim; check `secondary-publisher.xml` only to disambiguate, never to add values.

## Resources

- `references/entity-relation-schema.md` — entity/relation types and definitions.
- `references/alignment-rules.md` — merge vs. keep-separate rules.
- `references/exception-handling.md` — failure decision tree.
- `assets/graph.schema.json` — graph + extraction schema.
- `scripts/build_graph.py`, `scripts/query_graph.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input `extraction.json` (示意, 标注为示例):
```json
{"entities":[
  {"id":"e1","type":"material","label":"perovskite","mentions":[
     {"source_id":"primary","paragraph_id":"p3","quote":"perovskite absorber","surface":"perovskite"}]},
  {"id":"e2","type":"method","label":"LSTM","mentions":[
     {"source_id":"secondary","paragraph_id":"p7","quote":"long short-term memory (LSTM)","surface":"LSTM"}]}
 ],
 "merge_groups":[["e1"]],
 "relations":[{"id":"r1","type":"uses","source":"e2","target":"e1","direction":"e2->e1",
   "condition":"for efficiency prediction","evidence":[
     {"source_id":"secondary","paragraph_id":"p9","quote":"LSTM was applied to predict efficiency","strength":"direct"}]}],
 "conflicts":[]}
```
Call: `python scripts/build_graph.py --extraction extraction.json --manifest corpus-manifest.json --out graph.json`, then `query_graph.py`, then `write_result.py`. Sample output (示意): `graph.json` with nodes/edges/conflicts and `result.json` echoing `output_contract` fields.
