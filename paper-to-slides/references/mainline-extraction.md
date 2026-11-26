# Mainline extraction

Goal: rebuild the paper as a claim-first narrative skeleton, not a section-by-section copy.

## The skeleton (narrative block)

- `question` — the problem or gap the paper targets (its own words where possible).
- `approach` — the core method or idea, one or two clauses.
- `key_results` — 2–5 result statements, each tied to a figure or table.
- `conclusion` — the paper's own conclusion.
- `limitations` — scope, assumptions, and caveats the paper states.

## Separation rules

- **Own contribution vs. background.** The deck's claims must come from the paper's Results/Discussion/Conclusion, not from its Introduction's literature review. Prior work cited in the Introduction is context, not a claim of this paper.
- **Data vs. illustration.** Classify each figure/table as `experimental`, `computed`, or `schematic`. A schematic (e.g., an apparatus cartoon or a workflow diagram) may never be presented as evidence of a measured result.
- **This work vs. other work.** When a paragraph reports another group's number and then the authors' own, only the authors' own number supports a claim page; the other number belongs in a "context" bullet at most.

## Evidence grouping

- Every `key_result` must name at least one figure/table/equation/section reference with its page.
- Group results by the claim they support, not by the order they appear in the text.
- If two results support the same claim, put them on the same page; if one result is the claim itself, give it its own page.

## Fidelity rules (no silent rewrites)

- Numbers and units are copied exactly (significant figures, ranges, ± values).
- Method names and model names keep the paper's spelling and casing.
- Conclusion wording keeps the paper's hedge strength: "表明" vs "证实" vs "可能" must not be upgraded or downgraded.
- If a value is ambiguous or illegible, mark it in `uncertainty`; do not guess.
