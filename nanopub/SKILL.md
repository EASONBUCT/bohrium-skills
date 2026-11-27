---
name: nanopub
description: Split a paper's conclusions into individual, checkable assertions and bind each to its minimal evidence (verbatim quote + source location) and provenance (paper, authors, year, version), then export a machine-readable nanopub structure. The script reads the real material, splits sentences deterministically, and writes result.json echoing the task.md output_contract fields under /app/output. Use when a case provides a paper and asks for assertion decomposition, evidence binding, source tracing, or nanopub export. Do not use for graph building or reference management.
---

# Paper → assertions + evidence + provenance (nanopubs)

One command produces the nanopubs. The script splits the text into candidate
assertions and binds evidence/provenance; you (the agent) supply finer
subject–predicate–object triples and confidence via `annotations.json`.

## Procedure (minimal)

1. Read `/input/case.json` and `/input/task.md` for `case_id` and the
   `output_contract` fields. Identify the paper file under `/input`.
2. (Optional) Write `/app/work/annotations.json` with `assertions` (list of
   `{subject, predicate, object, evidence, paragraph_id, confidence}`) for the
   claims you want to decompose more finely than one sentence.
3. Run:
   ```
   python scripts/run.py --input /input --work /app/work --output /app/output
   ```
4. Confirm `/app/output/nanopubs.json` and `/app/output/result.json` exist.

## What run.py does (deterministic, verifiable)

- Reads JSON paragraphs, or runs `pdftotext` for a PDF, or reads `.txt`/`.md`.
- Splits into sentences; every sentence becomes a candidate assertion with its
  evidence quote and source `paragraph_id`.
- Attaches provenance (source_id, title, authors, year, doi, license) read from
  the corpus manifest or case.
- Exports a machine-readable structure (`assertion`, `evidence`, `provenance`,
  `confidence`) so downstream programs can parse it directly.
- Writes `nanopubs.json` and `result.json`.

## annotations.json (optional, illustrative)

```json
{"assertions":[{"subject":"the method","predicate":"improves","object":"accuracy by 5%",
                "evidence":"Our method improves accuracy by 5%.",
                "paragraph_id":"c1","confidence":"direct"}]}
```

## Output under /app/output

- `nanopubs.json` — provenance + nanopublications + stats.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources`
  + `uncertainty` + `change_log` + `nanopublications`.

## Failure handling

- No paper material → `status: partial`, flagged. An assertion with no
  supporting evidence is marked, not silently accepted. Full tree in
  `references/exception-handling.md`.

## Resources

- `references/nanopub-schema.md`, `references/evidence-rules.md`,
  `references/exception-handling.md`
- `assets/nanopub.schema.json`
- `scripts/run.py`
