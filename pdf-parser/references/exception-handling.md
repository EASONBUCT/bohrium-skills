# Failure handling decision tree

For each failure, record it in `result.json.uncertainty` or `change_log`, produce
what is honestly available, and continue. Never fabricate text, a tool, or a log.

## PDF-level problems

- **Encrypted / password-protected** → try the password only if the case gives
  one; otherwise `status: partial`, `uncertainty: "encrypted"`, no content.
- **No text layer (scanned)** → `pdftoppm -r 200` then OCR; tag `uncertainty:
  "OCR, low confidence"` and never fill a gap by guessing.
- **Corrupt PDF** → record the tool error; do not invent content.
- **pdftotext unavailable** → report it and stop the dependent step; the parse is
  empty with `has_text_layer: false`.

## Layout problems

- **Cross-column bleed / wrong order** → re-order by the page's detected column
  boundaries; verify against `pdftoppm` renders.
- **Full-width bottom element mis-assigned to a column** → if block width > 60%
  page width, place it by y after both columns; log the correction.
- **Header/footer mixed into body** → rely on the cross-page repetition test; if
  a single-page header slips through, drop it and log.

## Table problems

- **Merged/spanning cells** → keep raw text, mark `kind: image` or `uncertainty:
  "merged cells"`.
- **Multi-level header** → keep reconstructed rows, verify against the render.
- **Cross-page continued table** → report per-page fragments; join only on a
  repeated header.
- **Image-only table** → page/bbox + `kind: image`.

## Content problems

- **Formula glyphs lost / ambiguous Greek letters** → keep verbatim glyphs, mark
  `uncertainty`.
- **Illegible number** → mark `uncertainty`, never re-round or infer.

## Budget problems

- Save `parsed.json` first (cheap and deterministic). Then run the model review.
  If time runs out, write `result.json` with `status: partial` from the
  un-reviewed parse — it still carries full page/bbox evidence.
