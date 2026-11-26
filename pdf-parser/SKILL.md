---
name: pdf-parser
description: Parse a research PDF into structured, evidence-mapped results: corrected multi-column reading order, section hierarchy, tables reconstructed as rows/columns, figure/table/equation captions, verbatim text, and page + bounding-box coordinates for every element. Use when a case provides a PDF under /input and asks for document parsing, extraction, reading, question-answering, or knowledge structuring whose result.json must echo the task.md output_contract fields under /app/output. Do not use for generating slides, polishing prose, or interpreting scientific meaning.
---

# PDF → Structured Parse

Turn one research PDF into a structured, verifiable parse: ordered text, sections, tables, captions, equations, and references — each element pointing back to its page and block. The output is not "a wall of text"; it is layout-aware and traceable.

## Runtime contract (authoritative)

- Read the real inputs under `/input/case.json` and `/input/task.md`. `task.md` declares the `output_contract` fields that `result.json` must echo. The PDF is provided as material; read the actual file, never trust filenames or labels.
- Work in `/app/work` (scratch). Final artifacts go under `/app/output`.
- `/app/output/result.json` must contain **every** original `output_contract` field from `task.md`, plus `case_id`, `status`, `sources`, `uncertainty`, and `change_log`. Missing, undecidable, and failed parts are stated explicitly — never fabricated.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial results early.
- Do not invent scores, logs, software state, or document content. A partial parse names its limits.

## Inputs to collect first

1. `/input/case.json` — `case_id`, PDF path, any per-case constraints.
2. `/input/task.md` — the exact `output_contract` fields and completion criteria.
3. The PDF — resolve from `case.json`, then `task.md`, then by searching `/input`. If still absent, record the gap and continue on what exists.

## Procedure (in order)

### 1. Read the case
Record `case_id`, PDF path, and the `output_contract` field names into a scratch notes file under `/app/work`.

### 2. Inspect the PDF
Run `pdfinfo paper.pdf` to get page count and whether it is encrypted. Run `pdftotext -f 1 -l 1 paper.pdf -` and check whether any text comes back (text layer present vs. scanned image).

### 3. Parse with the deterministic parser
```
python scripts/parse_pdf.py --pdf /input/<paper>.pdf --out /app/work/parsed.json
```
This runs `pdftotext -tsv` (word coordinates) and does layout analysis: line/block grouping, multi-column reading order, heading/section detection, table reconstruction, caption/equation/reference extraction, and page+bbox evidence for every element. See `references/layout-order.md`, `references/table-extraction.md`, `references/structure-rules.md` for the exact rules.

### 4. Handle the hard cases
- **No text layer (scanned PDF)** → render with `pdftoppm -r 200`, run OCR on the page images, and put OCR text into the parse with `uncertainty: "OCR, low confidence"`.
- **Encrypted PDF** → if a password is provided in the case, use it; otherwise record `status: partial`, `uncertainty: "encrypted"` and parse nothing.
- **Image-only tables/formulas** → record their page/bbox and mark `kind: image`, not as reconstructed text.

### 5. Verify and correct (model review)
The parser is deterministic but not perfect. After running it, read `/app/work/parsed.json` and fix:
- reading-order mistakes on full-width bottom elements (equations/wide figures);
- headings the font-size heuristic missed or over-called;
- table grids with merged cells or multi-level headers (re-check against the rendered page image `pdftoppm -r 150`).
Record every correction in `change_log`. Do not silently "improve" the paper's wording — the text must stay verbatim.

### 6. Assemble result.json
```
python scripts/write_result.py --parsed /app/work/parsed.json \
  --case /input/case.json --out /app/output/result.json \
  --output-contract '{"<field>":"<value>",...}' --status complete
```
The script merges the `output_contract` fields (copied from `task.md`), `case_id`, and the parse summary with honest `status`, `sources`, `uncertainty`, `change_log`.

## Output layout under /app/output

- `parsed.json` — the full structured parse (blocks, sections, tables, figures, equations, references, each with page/bbox).
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log` (+ the parse summary the rubric asks for).

## Definition of done (check each before writing result.json)

- [ ] Text is extracted verbatim (no silent reword/re-round of numbers or symbols).
- [ ] Multi-column blocks are in the correct reading order, not concatenated across columns.
- [ ] Headings form a section hierarchy; title/abstract/sections/references are separated.
- [ ] Tables are reconstructed as rows/columns (or marked as image when not reconstructable).
- [ ] Every element has page + bbox evidence, or an explicit `uncertainty` note.
- [ ] Scanned/encrypted/illegible parts are marked honestly, never guessed.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full tree in `references/exception-handling.md`. Headlines:
- No text layer → OCR; mark confidence, never fill gaps by guessing.
- Encrypted → partial, state the reason.
- Cross-column bleed / wrong order → re-order by the page's column boundaries; verify against rendered page.
- Merged cells / multi-level table headers → keep the raw block and mark `kind: image` if the grid cannot be trusted.
- Formula glyphs lost → keep verbatim glyphs from pdftotext; mark `uncertainty` when a symbol is ambiguous.

## Resources

- `references/layout-order.md` — column detection and reading-order rules.
- `references/table-extraction.md` — table/grid reconstruction rules.
- `references/structure-rules.md` — heading/caption/equation/reference identification.
- `references/exception-handling.md` — failure decision tree.
- `assets/output.schema.json` — structured parse output schema.
- `scripts/parse_pdf.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input (示意, one paragraph): `python scripts/parse_pdf.py --pdf sample.pdf --out parsed.json`.
`parsed.json` (示意片段):
```json
{"blocks": [{"id":"p1-b2","type":"paragraph","text":"The thermal conductivity ...",
  "page":1,"bbox":[61.2,135.1,293.3,213.4],"order":2}],
 "sections": [{"id":"sec-1","level":1,"title":"1 Introduction","page":1}],
 "tables": [{"id":"tab-1","grid":{"columns":3,"rows":[["T (K)","k (W/m.K)","err (%)"]]}}]}
```
Then `write_result.py` produces `result.json` echoing the `output_contract` fields. Sample output (示意): `result.json` with `status: complete` and per-element page/bbox evidence.
