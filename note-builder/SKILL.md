---
name: note-builder
description: Turn a paper into structured, reusable notes: a paper card with the five core fields (research question, data, method, main findings, limitations) plus per-section notes, every note anchored to its source location (paragraph id / page) with a verbatim quote. The script reads the real material (JSON paragraphs, PDF, or text), splits sections deterministically, extracts anchors, and writes result.json echoing the task.md output_contract fields under /app/output. Use when a case provides a paper and asks for section-aligned summaries, a paper card, knowledge-point extraction, or anchor-linked notes. Do not use for graph building or reference management.
---

# Paper → fielded, anchor-linked notes

One command produces the notes. The script reads the paper and builds the
structure; you (the agent) supply richer section summaries and card text via
`annotations.json`, which the script merges and anchors.

## Procedure (minimal)

1. Read `/input/case.json` and `/input/task.md` for `case_id` and the
   `output_contract` fields. Identify the paper file under `/input`.
2. (Optional) Write `/app/work/annotations.json` with `section_summaries`
   (list of `{section, summary}`) and `card` (field name → `{text}`) for the
   five fields.
3. Run:
   ```
   python scripts/run.py --input /input --work /app/work --output /app/output
   ```
4. Confirm `/app/output/notes.json` and `/app/output/result.json` exist.

## What run.py does (deterministic, verifiable)

- Reads JSON paragraphs, or runs `pdftotext` for a PDF, or reads `.txt`/`.md`.
- Splits into sections by headings (Abstract/Methods/Results/… and numbered
  headings), so notes follow the paper's own structure, not a generic template.
- Builds the 5-field paper card; each field is anchored to a paragraph id with
  a verbatim quote, and marked `uncertain` when the source section is absent.
- Extracts key items (citation markers, numbers with units) per section.
- Writes `notes.json` and `result.json`.

## annotations.json (optional, illustrative)

```json
{"section_summaries":[{"section":"Results","summary":"..."}],
 "card":{"research_question":{"text":"..."}}}
```

## Output under /app/output

- `notes.json` — paper card + section notes + stats.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources`
  + `uncertainty` + `change_log` + `paper_card` + `sections`.

## Failure handling

- No paper material → `status: partial`, flagged. Full tree in
  `references/exception-handling.md`.

## Resources

- `references/note-fields.md`, `references/anchor-rules.md`,
  `references/exception-handling.md`
- `assets/note.schema.json`
- `scripts/run.py`
