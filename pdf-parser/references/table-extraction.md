# Table extraction and reconstruction

Tables are handled two ways, depending on how the PDF stored them.

## Case A: one block, multiple aligned lines

When a table is a single text block (common in LaTeX/Word exports), it is
detected by `looks_like_table`: ≥ 3 lines that share large inter-word gaps
(column gutters) at least 2.5× the median word gap and > 10 pt. Running prose
never has such gutters, so paragraphs are not misread as tables.

Reconstruction clusters word x-positions into columns, then emits one row per
line with cells joined per column.

## Case B: each cell is its own block

Some PDFs render each cell as a separate text block. `detect_grid_tables`
collects single-line blocks with ≤ 3 words (excluding headings and captions),
clusters their y-tops into rows and x-lefts into columns, and rebuilds the grid.
It keeps a table only when ≥ 70% of cells are filled, to avoid false positives.

## Limits (state honestly, do not guess)

- **Merged cells / spanning cells** — the grid reconstruction may drop or
  misplace a spanning cell. When the grid cannot be trusted, keep the raw block
  text and mark `kind: image` (or `uncertainty: "merged cells"`).
- **Multi-level headers** — treat the first reconstructed rows as header rows
  but verify against the rendered page (`pdftoppm -r 150`).
- **Cross-page continued tables** — each page's fragment is reported separately
  with its own page/bbox; the agent joins them only when a repeated header row
  confirms the continuation.
- **Image-only tables** — no text layer means no reconstruction; record the
  page/bbox and mark `kind: image`.
