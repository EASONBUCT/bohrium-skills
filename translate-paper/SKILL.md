---
name: translate-paper
description: Translate a research paper (or a paragraph range) into a verifiable bilingual result. The script reads the source directly, segments paragraphs 1:1, extracts a terminology table, merges the agent's translations, and verifies that numbers, units, citation markers, and figure/table references are preserved; it writes result.json echoing the task.md output_contract fields under /app/output. Use when a case provides a paper (PDF or text) under /input and asks for literature translation, bilingual alignment, or 译文核验. Do not use for slides, note-taking, or reference management.
---

# Paper → verifiable bilingual translation

One command assembles the bilingual result. The script reads the source and does
all deterministic work (segmentation, terminology, verification); you (the
agent) only supply the actual translations via `annotations.json`.

## Procedure (minimal)

1. Read `/input/case.json` and `/input/task.md` for `case_id`, source/target
   language, and the `output_contract` fields. Identify the paper under `/input`.
2. Read the source and translate it. Write `/app/work/annotations.json`:
   ```json
   {"translations": [{"paragraph_id": "p1", "translation": "..."}],
    "terminology": [{"source": "thermal conductivity", "target": "热导率"}]}
   ```
3. Run:
   ```
   python scripts/run.py --input /input --work /app/work --output /app/output
   ```
4. Confirm `/app/output/translation.json` and `/app/output/result.json` exist,
   and that any untranslated segment is listed, not silently left blank.

## What run.py does (deterministic, verifiable)

- Reads the paper (JSON paragraphs, PDF via `pdftotext -layout`, or text) and
  segments it 1:1 by `para_id` — no omission, no duplication.
- Extracts a terminology table (acronyms, repeated terms) and locks the agent's
  term renderings, recording `first_seen`.
- Merges the agent's translations by `paragraph_id`.
- Verifies per segment that numbers, units, citation markers, and figure/table
  references in the source still appear in the translation (`missing_tokens`).
- Lists `untranslated_segments` honestly; writes `translation.json` + `result.json`.

## Failure handling

- No text layer / scanned PDF → run `pdftoppm` + OCR and mark `uncertain`; never
  invent text. A part you cannot verify goes into `verification`/`unclear`.
  Full tree in `references/exception-handling.md`.

## Resources

- `references/translation-rules.md`, `references/verification-rules.md`,
  `references/exception-handling.md`
- `assets/translation.schema.json`
- `scripts/run.py`
