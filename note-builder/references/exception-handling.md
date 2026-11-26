# Failure handling decision tree

Record each failure in `result.json.uncertainty` or `change_log`, produce what is
honestly available, and continue. Never fabricate paper content, a field, a score,
or a tool log.

## Document problems

- **Scanned PDF (no text layer)** → `pdftoppm -r 200` + OCR; mark
  `uncertainty: "OCR, low confidence"`; never fill a gap by guessing.
- **Encrypted / permission-restricted** → try the password only if the case gives
  one; otherwise `status: partial`, `uncertainty: "encrypted"`, no content.
- **Two-column order wrong** → re-order by the page's column boundaries, verify
  against a rendered page (`pdftoppm`).
- **Missing figures/tables/formulas** → record their location and mark
  `kind: image`, never reconstruct a value from an image.
- **Very long paper** → summarize section by section; if truncated, state which
  sections were not covered.

## Content problems

- **Field not reported by the paper** → `未报告`; do not invent from background.
- **Finding missing its condition** → keep the finding but mark
  `uncertainty: "condition not stated"`.
- **Alias/abbreviation ambiguity** → keep separate entries + a note; do not
  merge silently.
- **Two statements conflict** → keep both, mark `uncertainty: "conflict"`.
- **Non-Chinese / non-English text** → keep verbatim; translate only if the
  contract asks, and mark the translation as `translated`.

## Budget problems

- Save `notes.json` first (deterministic, cheap). If time runs out, write
  `result.json` with `status: partial` from the notes built so far — they still
  carry anchors.
