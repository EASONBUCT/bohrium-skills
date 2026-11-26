# Multi-column reading order

The parser extracts word coordinates with `pdftotext -tsv`, groups words into
lines and blocks, then orders blocks so that a two-column paper is read as
"left column top-to-bottom, then right column top-to-bottom" — never as a single
interleaved stream.

## Column detection

- Compute each block's x-center.
- Split the page into 2 columns only when both halves are populated and the mean
  centers are separated by > 18% of the page width. Otherwise treat as 1 column.
- The split threshold avoids breaking narrow single-column layouts.

## Reading order

- Within a column, order blocks by top (y0) ascending.
- Order columns left-to-right.
- Blocks assigned to the left column come before blocks assigned to the right
  column, regardless of absolute y — this is what prevents cross-column bleed.

## Known limitation and its fix

- A **full-width element at the bottom** (a wide equation or figure that spans
  both columns) can be mis-assigned to the left column if its x-center is left of
  the page center. The SKILL instructs the agent to detect such wide blocks
  (block width > 60% page width) and re-place them by y-position after both
  columns at that height, then record the correction in `change_log`.

## Header / footer

- Text that repeats at the very top or bottom across ≥ 2 pages is a running
  header/footer (`margin`), not body text. It is never mixed into the body.
