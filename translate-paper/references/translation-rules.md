# Translation rules

## Terminology lock ("术语稳")

- Extract every domain term and fix one target-language rendering.
- The same source term renders the same way in title, abstract, body, captions,
  and conclusions. The table is the source of truth, not a suggestion.
- Record `first_seen` (where the term first appears) so abbreviation/definition
  can be placed correctly.

## Segmentation ("段落全")

- Split at semantic boundaries (paragraph, sentence) — never mid-sentence.
- Carry the locked terms and the preceding sentence's context into each segment.
- `para_id` matches the source 1:1. No omission, no duplication, no misalignment
  across pages, columns, or chapter breaks.
- Long text: translate section by section, keep the running `para_id` sequence.

## Alignment ("可核验")

- Output a bilingual paragraph-level pair: source text + translation per `para_id`.
- Keep sentence boundaries so a reader can point to the source sentence.
- A translated passage that paraphrases rather than translates is flagged, not
  passed off as a translation.

## Reference/negation ("关系准")

- Reference pronouns resolve to the intended antecedent; do not leave an ambiguous
  "it/this" that could point to the wrong object.
- Negation scope, limitations, cause vs concession stay as the source states them.
