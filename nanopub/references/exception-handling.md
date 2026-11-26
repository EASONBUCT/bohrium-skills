# Failure handling decision tree

Record each failure in `result.json.uncertainty` or `change_log`, produce what is
honestly available, and continue. Never fabricate an assertion, evidence, source,
score, or tool log.

## Document problems

- **Scanned PDF (no text layer)** → `pdftoppm -r 200` + OCR; mark
  `uncertainty: "OCR, low confidence"`; never guess a value.
- **Encrypted / inaccessible** → `status: partial`, `uncertainty: "encrypted"`,
  no content.
- **Two-column order wrong** → re-order by column boundaries, verify against a
  rendered page.
- **Evidence crosses a figure/table** → record figure/table + caption location;
  do not reconstruct a value from an image.
- **Very long paper** → process conclusion-bearing sections first; state which
  sections were not covered.

## Assertion problems

- **Compound sentence** → split into clauses; if a clause is not independently
  verifiable, do not emit it as an assertion.
- **Too broad (over-claiming)** → narrow the `scope`; if it cannot be narrowed,
  flag `quality: too-broad`.
- **No supporting fragment** → flag `unsupported`, do not invent evidence.
- **Subject/predicate confusion** → fix subject and predicate direction; log the
  change.
- **Evidence contradicts the assertion** → keep the raw quote, flag
  `quality: conflict`.

## Source problems

- **Missing DOI/year/version** → `未报告`; never fabricate.
- **Paper metadata at the root belongs to one paper only** → do not apply it to
  a second paper.

## Budget problems

- Save `nanopubs.json` first (deterministic, cheap). If time runs out, write
  `result.json` with `status: partial` from what was exported.
