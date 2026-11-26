# Structure identification rules

Order matters: caption → numbered/known heading → title → equation → font-size
heading → reference → table → paragraph.

## Heading

- Numbered pattern: `1.`, `2.3`, `1.2.1` followed by a title → heading with
  level = number of dot-separated parts.
- Known names: Abstract, Introduction, Results, Methods, Discussion, Conclusion(s),
  References, Bibliography, Appendix, Supplementary, etc.
- Font-size fallback: a short block (≤ 20 words) whose line height is ≥ 1.18× the
  document median body height.

## Title

- A block near the very top (< 10% page height) whose font is ≥ 1.25× body size
  and which is not a numbered heading → the paper title.

## Caption

- `Fig. / Figure / Table / Scheme / Algorithm / Chart / Eq. / Equation` followed
  by a number. Figure captions go to `figures`; table captions go to `tables`
  as caption-only entries.

## Equation

- A centered block (x-center within 18% of page center) that is short and
  contains math markers (`=`, `±`, Greek letters, `∑`, `∫`, `√`, etc.). Formulas
  are kept verbatim; a formula rendered as an image is marked `kind: image`.

## Reference entry

- `[n]` or `n.` at the start of a line (typically inside the References section).

## Margin (header/footer)

- Text that repeats at the very top or bottom across ≥ 2 pages.

## Fidelity

- All text is joined verbatim from extracted words; spaces are inferred from the
  word-gap distribution, never from assumed content.
- Numbers, units, Greek letters, and special characters are not reworded or
  re-rounded. Ambiguous glyphs go to `uncertainty`.
