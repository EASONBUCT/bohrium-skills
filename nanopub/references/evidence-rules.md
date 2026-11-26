# Evidence binding rules

Each assertion must bind a minimal sufficient evidence fragment and its exact
location. "Minimal sufficient" = the shortest verbatim fragment that makes the
assertion checkable, without extra context that changes the meaning.

## Granularity

- One assertion → one or more fragments; each fragment supports that assertion.
- A fragment must actually contain the subject, predicate, and object as the
  paper states them.
- Do not bind a whole paragraph when one sentence suffices; do not trim a
  sentence so much that its condition is lost.

## Strength

- `direct` — the paper states the assertion verbatim.
- `inferred` — the assertion follows clearly from the fragment (e.g. a number in
  a results table), and you say so in `confidence.basis`.
- **Not evidence**: co-occurrence, a review's paraphrase of another paper, or a
  model's background knowledge. Flag these as `unsupported`.

## Location

- PDF → `location` is the page number. Paragraph-indexed input → `paragraph_id`.
  Never invent a page.
- A claim from a figure/table → record `location` as the figure/table number +
  its caption location; the quote is the caption text.

## Conflicts

- If a fragment contradicts the assertion, do not "fix" the assertion silently:
  record the raw fragment and mark `quality: conflict`.
