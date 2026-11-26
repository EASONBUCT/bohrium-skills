# Cross-paper entity alignment rules

The goal is: same concept in both papers = one node; different concept that
shares a generic name = separate nodes, recorded as a conflict.

## Merge (one node) only when

- The two mentions are an alias/abbreviation pair of the same entity, e.g.
  "long short-term memory" ↔ "LSTM", "MAPbI3" ↔ "methylammonium lead iodide".
- Or the same exact surface form refers to the same thing, AND there is positive
  evidence of identity (same definition, same identifier, cross-reference).
- Record `merged_from` (the entity ids folded in) and `merge_justification`
  (the reason, e.g. "abbreviation expansion").

## Keep separate (record a conflict) when

- The same generic term refers to different physical samples / model instances /
  datasets / experimental conditions across the two papers. Example: both papers
  say "LSTM" but train different models on different data.
- There is a same-name conflict (homonym) with no evidence of identity.
- Record `conflicts` as `{"kind": "same-name-different-object", "nodes": [...],
  "reason": "..."}`.

## Never

- Force every alias to merge.
- Merge based only on a shared generic word ("deep learning", "graphene") without
  identity evidence.
- Treat two file formats of the same paper as cross-paper evidence.
- Combine the two papers' conditions, sample counts, or numeric results into one
  merged claim.

## Bookkeeping

- A merged node keeps the canonical label and all mentions from every merged id,
  so every mention remains traceable to its own `source_id` + `paragraph_id`.
- The `merged_from` list preserves the pre-merge ids for review.
