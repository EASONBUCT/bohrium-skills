---
name: nanopub
description: Turn a paper's key conclusions into nanopublications: split each passage into single, independently verifiable assertions (subject–predicate–object with conditions and scope), bind each to a minimal sufficient evidence fragment with its exact location, and attach full source metadata (paper, authors, year, version, DOI) plus publication info and confidence — exported as machine-readable JSON. Use when a case provides a paper (PDF or paragraph-indexed text) under /input and asks for nanopublication generation, assertion extraction, evidence binding, or provenance export whose result.json must echo the task.md output_contract fields under /app/output. Do not use for slides, plain notes, or knowledge-graph edges.
---

# Paper → Nanopublications

Split a paper's conclusions into atomic, checkable assertions and export them as nanopublications: each one carries its assertion (subject–predicate–object + condition), its minimal supporting evidence with location, its source metadata, and its publication info. The result is machine-readable and traceable back to the original text.

## Runtime contract (authoritative)

- Read the real inputs under `/input/case.json` and `/input/task.md`. `task.md` declares the `output_contract` fields `result.json` must echo. The paper is provided as material; read the actual file.
- Work in `/app/work`. Final artifacts under `/app/output`, including `result.json` with every `output_contract` field, `case_id`, `status`, `sources`, `uncertainty`, `change_log`.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial results early.
- Do not invent scores, logs, or paper content. A partial export names its limits.

## Inputs to collect first

1. `/input/case.json` + `/input/task.md` — `case_id`, `output_contract` fields, paper path.
2. The paper — resolve from `case.json`, then `task.md`, then search `/input`. PDF or paragraph-indexed text.

## Procedure (in order)

### 1. Read the case
Record `case_id`, paper path, and the `output_contract` field names.

### 2. Get the paper text
- PDF with text layer → `pdftotext -layout paper.pdf out.txt` (or the platform `pdf-text-tool`), keeping page markers.
- Paragraph-indexed JSON → read `paragraph_id` fields directly.
- Scanned PDF → `pdftoppm` + OCR, mark `uncertainty: "OCR"`.

### 3. Split into assertions
Break each conclusion-bearing passage into single assertions, each independently true-or-false. Handle compound sentences (并列 and 因果) by separating their clauses. Keep conditions and scope (e.g. "at 300 K", "on dataset D", "for method M"). Rules in `references/nanopub-schema.md`. Do not stuff a whole paragraph into one assertion field.

### 4. Bind evidence
For each assertion, find the minimal sufficient verbatim fragment that supports it, and record its exact location (page or paragraph_id). Distinguish `direct` evidence (stated) from `inferred` (clearly implied); a review paraphrase or co-occurrence is not evidence. Rules in `references/evidence-rules.md`.

### 5. Record source metadata
Paper title, authors, year, version, DOI/identifier, and data source as they appear. Never guess a DOI or year; mark `未报告` when absent.

### 6. Quality check
Reject or flag: assertions that are too broad; evidence that does not actually support the assertion; wrong subject/predicate/relation; missing source. Record the reproducible reason for each rejection. Controlled relation vocabulary in `references/nanopub-schema.md`.

### 7. Assemble and export
```
python scripts/build_nanopubs.py --extraction /app/work/extraction.json \
  --out /app/work/nanopubs.json
python scripts/write_result.py --nanopubs /app/work/nanopubs.json \
  --case /input/case.json --out /app/output/result.json \
  --output-contract '{"<field>":"<value>",...}' --status complete
```
`extraction.json` is written by you (the agent) following `assets/nanopub.schema.json`; the scripts are deterministic. `nanopubs.json` is machine-readable (strict JSON, stable ids).

## Output layout under /app/output

- `nanopubs.json` — the list of nanopublications: assertion + evidence + provenance + publication info + confidence.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log`.

## Definition of done (check each before writing result.json)

- [ ] Passages are split into single verifiable assertions, not whole-paragraph strings.
- [ ] Each assertion keeps its subject, predicate (controlled vocabulary), object, condition, and scope.
- [ ] Each assertion binds a minimal sufficient verbatim evidence fragment with a real location.
- [ ] Evidence strength is `direct` or `inferred`; unsupported assertions are flagged, not exported as fact.
- [ ] Source metadata (paper/authors/year/version/DOI) is real; missing fields are `未报告`.
- [ ] Output is strict, machine-readable JSON with stable identifiers.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full tree in `references/exception-handling.md`. Headlines:
- Scanned PDF → OCR + mark confidence; never guess.
- Assertion with no supporting fragment → flag `unsupported`, do not invent evidence.
- Assertion conflicts with the evidence → flag `conflict`, keep the raw quote.
- Missing source metadata → `未报告`, never fabricate DOI/year.
- Cross-chart evidence → record figure/table + caption location.

## Resources

- `references/nanopub-schema.md` — assertion fields, controlled relation vocabulary, source metadata.
- `references/evidence-rules.md` — minimal-sufficiency and evidence-strength rules.
- `references/exception-handling.md` — failure decision tree.
- `assets/nanopub.schema.json` — nanopublication output schema.
- `scripts/build_nanopubs.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input `extraction.json` (示意, 标注为示例):
```json
{"source":{"title":"...","authors":"...","year":2024,"doi":"..."},
 "nanopubs":[{"id":"np-1",
   "assertion":{"subject":"LSTM","predicate":"outperforms","object":"baseline",
     "condition":"on the 2019 test split","scope":"single dataset"},
   "evidence":[{"quote":"LSTM outperformed the baseline on the 2019 test split",
     "location":"p14","strength":"direct"}],
   "confidence":{"basis":"stated in Results","value":"high"}}]}
```
Call `build_nanopubs.py` then `write_result.py`. Sample output (示意): `nanopubs.json` and `result.json` echoing `output_contract` fields.
