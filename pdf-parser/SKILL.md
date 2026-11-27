---
name: pdf-parser
description: Parse the PDF(s) under /input into structured blocks — title, authors, abstract, section headings, paragraphs, figure/table captions, tables, formulas, and references — each with its page number, block id, and verbatim text. The script runs pdftotext itself so the text is genuinely extracted from the real file, classifies blocks deterministically, and writes result.json echoing the task.md output_contract fields under /app/output. Use when a case provides an actual PDF and asks for text extraction, reading order, section/structure recognition, table/caption/formula extraction, or OCR. Do not use for graph building or note-taking.
---

# PDF → structured blocks (page, type, verbatim text)

One command parses the PDF. The script extracts the text with `pdftotext -layout`
itself (no pre-extracted answer layer) and classifies blocks by rule; you (the
agent) only need to check the layout flags if a case is a scanned PDF.

## Procedure (minimal)

1. Read `/input/case.json` and `/input/task.md` for `case_id` and the
   `output_contract` fields. Identify the PDF under `/input`.
2. Run:
   ```
   python scripts/run.py --input /input --work /app/work --output /app/output
   ```
3. Confirm `/app/output/parsed.json` and `/app/output/result.json` exist. Each
   block has `block_id`, `page`, `type`, and verbatim `text`.

## What run.py does (deterministic, verifiable)

- Runs `pdftotext -layout` (falls back to plain `pdftotext`) and splits by page
  form-feed, so page numbers are the real PDF page numbers.
- Merges lines into blocks on blank lines and classifies each block:
  `heading` (section keywords / numbered headings), `caption` (Fig./Table),
  `reference` ([n] / numbered with year or et al.), `formula` (math symbols /
  standalone equation number), else `paragraph`.
- Reports `stats` (pages, blocks, count by type) and any extraction errors.
- Falls back to `.txt`/`.md` input if no PDF is present.

## Output under /app/output

- `parsed.json` — blocks + per-type stats + errors.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources`
  + `uncertainty` + `change_log` + `blocks`.

## Failure handling

- Scanned PDF / no text layer → run `pdftoppm` + OCR and mark the blocks
  `uncertain`; never invent text. Encrypted PDF → report in `uncertainty`.
  Full tree in `references/exception-handling.md`.

## Resources

- `references/layout-order.md`, `references/structure-rules.md`,
  `references/table-extraction.md`, `references/exception-handling.md`
- `assets/output.schema.json`
- `scripts/run.py`
