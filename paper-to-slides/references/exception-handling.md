# Failure handling decision tree

For each failure, record it in `result.json.uncertainty` or `change_log`, produce what is honestly available, and continue. Never fabricate a missing file, tool, number, or log.

## Paper unreadable

- **PDF encrypted / password-protected** → try `pdftotext -upw` only if a password is given in the case; otherwise record "encrypted, cannot extract" and produce a partial deck from the abstract/metadata if any.
- **Scanned PDF (no text layer)** → run OCR; if OCR output is low-confidence, mark pages `uncertainty: "ocr, low confidence"`.
- **Corrupt PDF** → record the tool error; do not guess content.

## Content-level problems

- **Equation is an image / formula lost** → keep the verbatim image or the paper's LaTeX as-is; mark `uncertainty: "equation reproduced verbatim from image"`.
- **Figure number in text ≠ figure in file** → trust the figure's own caption page; record the mismatch.
- **Ambiguous/illegible number** → mark `uncertainty`, do not re-round or infer.

## Template problems

- **Placeholder insufficient / wrong type** → use the master's blank layout and add minimal text boxes; preserve theme.
- **Fonts missing** → run font-discovery; substitute a coverage-complete sans/serif; record the change.
- **Starting deck given** → edit the given deck; do not start from a blank template.

## Output problems

- **Slide count exceeded** → merge support pages first, keep one-claim-per-page and the conclusion; record the compression.
- **Rendering fails (no PDF/PNG)** → keep the editable source deck; record the renderer error; mark previews `missing`.
- **python-pptx unavailable** → the build script falls back to a dependency-free OOXML writer; note `backend: stdlib-pptx` in the build summary.

## Budget problems

- Save the outline JSON and `evidence_map.json` first (cheap). Then build the deck. Then render. If time runs out, submit the outline + evidence map as a partial result with an explicit `status: partial`.
