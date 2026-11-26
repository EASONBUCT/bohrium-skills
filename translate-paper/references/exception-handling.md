# Failure handling decision tree

Record each failure in `result.json.uncertainty` or `change_log`, deliver what is
honestly available, and continue. Never fabricate a translation, a term, a score,
or a tool log.

## Document problems

- **No text layer (scanned)** → `pdftoppm` + OCR; mark `uncertainty: "OCR"`;
  never guess a value.
- **Formula/table is an image** → mark `image` in the segment, do not reconstruct.
- **Reference list unparseable** → translate what is parseable, flag the rest.
- **Language-mixed source** → translate the target-language direction, keep
  non-source segments verbatim, flag if translation is required.

## Content problems

- **Term rendering uncertain** → fix a provisional rendering and list it in
  `unclear`; do not leave two renderings in the body.
- **Reference pronoun ambiguous** → resolve to the intended antecedent; if it
  cannot be resolved, flag it.
- **A sentence would need paraphrase to translate** → translate faithfully and
  note the deviation in `notes`; do not pass a rewrite as a translation.

## Budget problems

- Save `translation.json` early (deterministic, cheap). If time runs out, write
  `result.json` with `status: partial` and the segments translated so far.
