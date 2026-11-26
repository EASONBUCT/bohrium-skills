---
name: note-builder
description: Turn one research paper into structured, reusable notes: a paper card (research question, data, methods, conditions, findings, limitations), per-section summaries that follow the paper's own heading order, and retrievable knowledge points (concept/variable/method/conclusion) — every note bound to a section + paragraph/page + verbatim quote anchor. Use when a case provides a paper (PDF or paragraph-indexed text) under /input and asks for literature summary, structured notes, or paper card whose result.json must echo the task.md output_contract fields under /app/output. Do not use for slides, knowledge-graph edges, or raw PDF text extraction.
---

# Paper → Structured Notes

Produce notes that mirror the paper's own structure, keep the claims and their preconditions, and let every note be traced back to a specific place in the paper. The output is a reusable note, not a flattened abstract.

## Runtime contract (authoritative)

- Read the real inputs under `/input/case.json` and `/input/task.md`. `task.md` declares the `output_contract` fields `result.json` must echo. The paper is provided as material; read the actual file, never trust labels.
- Work in `/app/work`. Final artifacts under `/app/output`, including `result.json` with every `output_contract` field, `case_id`, `status`, `sources`, `uncertainty`, `change_log`.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial results early.
- Do not invent scores, logs, or paper content. A partial note names its limits.

## Inputs to collect first

1. `/input/case.json` + `/input/task.md` — `case_id`, `output_contract` fields, paper path.
2. The paper — resolve from `case.json`, then `task.md`, then search `/input`. PDF or paragraph-indexed text (JSON/Markdown).

## Procedure (in order)

### 1. Read the case
Record `case_id`, paper path, and the `output_contract` field names into `/app/work`.

### 2. Get the paper text
- PDF with a text layer → `pdftotext -layout paper.pdf out.txt` (or the platform `pdf-text-tool`). Keep page markers so anchors can cite pages.
- Paragraph-indexed JSON → read `paragraph_id` fields directly; anchors cite `paragraph_id`.
- No text layer (scanned) → `pdftoppm` + OCR, mark `uncertainty: "OCR"`.

### 3. Identify the paper's own section structure
Do not impose a generic template (Introduction/Methods/Results/Discussion). Read the actual heading order and titles, and mirror them. Record each section with its heading text and order. Rules in `references/note-fields.md`.

### 4. Fill the paper card
Extract, in the paper's own words wherever possible: research question, data/samples, methods and their conditions, main findings, and limitations. A finding must keep the condition that makes it true (e.g. "at 300 K", "on dataset D"). Missing items are marked `未报告`, not guessed.

### 5. Extract knowledge points
Split important concepts, variables, methods, and conclusions into retrievable entries. Normalize aliases/abbreviations (record them, do not duplicate). Conflicts between the paper's own statements stay visible, not silently merged. Rules in `references/note-fields.md`.

### 6. Bind anchors
Every note and knowledge point gets an anchor: `section`, `page` or `paragraph_id`, and a short verbatim `quote`. Granularity matches claim strength. Rules in `references/anchor-rules.md`.

### 7. Assemble
```
python scripts/build_notes.py --extraction /app/work/extraction.json \
  --out /app/work/notes.json
python scripts/write_result.py --notes /app/work/notes.json \
  --case /input/case.json --out /app/output/result.json \
  --output-contract '{"<field>":"<value>",...}' --status complete
```
`extraction.json` is written by you (the agent) following `assets/note.schema.json`; the scripts are deterministic.

## Output layout under /app/output

- `notes.json` — paper card + sections + knowledge points + anchors.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log`.

## Definition of done (check each before writing result.json)

- [ ] Sections mirror the paper's own heading order and titles (not a template).
- [ ] Paper card covers research question, data, methods, conditions, findings, limitations.
- [ ] Findings keep their preconditions; missing items are `未报告`.
- [ ] Knowledge points are deduplicated by alias/abbreviation; conflicts stay visible.
- [ ] Every note has a section + page/paragraph + verbatim quote anchor.
- [ ] Scanned/illegible parts are marked honestly, never guessed.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full tree in `references/exception-handling.md`. Headlines:
- Scanned PDF → OCR + mark confidence; never fill gaps by guessing.
- Encrypted / no text → partial note, state the reason.
- Two-column reading order wrong → fix by column boundaries, verify against render.
- Ambiguous alias → keep separate entries + note, do not merge silently.
- Conflicting statements → keep both, mark `uncertainty: "conflict"`.

## Resources

- `references/note-fields.md` — paper card fields, section rules, knowledge-point types.
- `references/anchor-rules.md` — evidence anchoring and granularity.
- `references/exception-handling.md` — failure decision tree.
- `assets/note.schema.json` — note output schema.
- `scripts/build_notes.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input `extraction.json` (示意, 标注为示例):
```json
{"paper_card": {"title":"...", "research_question":"...", "main_findings":["..."],
  "limitations":["..."]},
 "sections": [{"id":"sec-1","title":"Introduction","summary":"...","anchors":[
   {"page":1,"quote":"..."}]}],
 "knowledge_points":[{"id":"kp-1","type":"method","label":"LSTM","definition":"...",
   "anchors":[{"section":"Methods","page":3,"quote":"..."}]}]}
```
Call `build_notes.py` then `write_result.py`. Sample output (示意): `notes.json` and `result.json` echoing `output_contract` fields.
