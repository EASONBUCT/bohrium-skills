---
name: translate-paper
description: Translate a research paper (or a paragraph range) into a verifiable bilingual result: extract a terminology table and lock the same translation across title, abstract, body, captions, and conclusions; segment long text at semantic boundaries with paragraph numbers matched 1:1; preserve negation, limitation, cause/concession, numbers, units, formulas, and citation markers; and mark untranslatable/uncertain parts explicitly. Use when a case provides a paper (PDF or text) under /input and asks for literature translation, bilingual alignment, or 译文核验 whose result.json must echo the task.md output_contract fields under /app/output. Do not use for slides, note-taking, or reference management.
---

# Paper → verifiable bilingual translation

Translate the paper while keeping every number, unit, formula, citation, and logical relation intact, with the same term rendered the same way everywhere, and each translated paragraph traceable back to its source.

## Runtime contract (authoritative)

- Read the real inputs under `/input/case.json` and `/input/task.md`. `task.md` declares the `output_contract` fields `result.json` must echo. Material is provided as files; read the actual files.
- Work in `/app/work`. Final artifacts under `/app/output`, including `result.json` with every `output_contract` field, `case_id`, `status`, `sources`, `uncertainty`, `change_log`.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial deliverables early.
- Do not invent scores, logs, or translation content. The translation conveys what the source says, nothing more.

## Inputs to collect first

1. `/input/case.json` + `/input/task.md` — `case_id`, source/target language, the paragraph range to translate, and the `output_contract` fields.
2. The paper — PDF or paragraph-indexed text. Resolve from `case.json`, then `task.md`, then search `/input`.

## Procedure (in order)

### 1. Read the case
Record `case_id`, language direction, the paragraph range, and the `output_contract` fields.

### 2. Get the source text
- PDF with text layer → `pdftotext -layout` (or the platform `pdf-text-tool`), keeping page markers.
- Paragraph-indexed JSON → read `paragraph_id` directly.
- Scanned PDF → `pdftoppm` + OCR, mark `uncertainty: "OCR"`.

### 3. Build the terminology table
Extract domain terms and fix one target-language rendering per term. The same term must use the same rendering in title, abstract, body, captions, and conclusions. Rules in `references/translation-rules.md`.

### 4. Segment and translate
Split at semantic boundaries (not mid-sentence), carry context and locked terms forward, and translate paragraph by paragraph with `para_id` matching the source 1:1 — no omission, no duplication, no misalignment across pages/columns/chapters.

### 5. Verify
Check each translated paragraph against the source for: numbers, units, formulas, figure/table numbers, citation markers, negation scope, limitations, cause vs concession. Mark anything uncertain as `unclear`, never smooth it over. Rules in `references/verification-rules.md`.

### 6. Assemble
```
python scripts/build_translation.py --extraction /app/work/extraction.json \
  --out /app/work/translation.json
python scripts/write_result.py --translation /app/work/translation.json \
  --case /input/case.json --out /app/output/result.json \
  --output-contract '{"<field>":"<value>",...}' --status complete
```
`extraction.json` is written by you (the agent) following `assets/translation.schema.json`; the scripts are deterministic.

## Output layout under /app/output

- `translation.json` — terminology + aligned segments + verification + unclear list.
- `translation.md` — the bilingual paragraph-aligned result (source + translation per `para_id`).
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log`.

## Definition of done (check each before writing result.json)

- [ ] Terminology table exists and the same term is rendered identically everywhere.
- [ ] Every source paragraph has a 1:1 `para_id` and a translation (no omission/duplication).
- [ ] Numbers, units, formulas, figure/table numbers, citation markers are preserved.
- [ ] Negation scope, limitations, cause vs concession match the source.
- [ ] Unclear/uncertain parts are marked, not silently rendered.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full tree in `references/exception-handling.md`. Headlines:
- No text layer → OCR + mark confidence.
- Formula/table is an image → mark `image`, do not reconstruct.
- Term translation uncertain → fix a provisional rendering, list it in `unclear`.
- Reference list unparseable → translate what is parseable, flag the rest.

## Resources

- `references/translation-rules.md` — terminology lock, segmentation, alignment.
- `references/verification-rules.md` — number/unit/formula/citation/negation checks.
- `references/exception-handling.md` — failure decision tree.
- `assets/translation.schema.json` — translation output schema.
- `scripts/build_translation.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input `extraction.json` (示意, 标注为示例):
```json
{"source_language":"en","target_language":"zh",
 "terminology":[{"source":"thermal conductivity","target":"热导率","first_seen":"abstract"}],
 "segments":[{"para_id":"p1","source":"The thermal conductivity increases with temperature.",
   "translation":"热导率随温度升高而增大。","notes":""}],
 "verification":[{"para_id":"p1","numbers_ok":true,"units_ok":true,"citations_ok":true}],
 "unclear":[]}
```
Call `build_translation.py` then `write_result.py`. Sample output (示意): `translation.json` + `result.json` echoing `output_contract` fields.
