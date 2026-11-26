# Entity and relation schema

## Entity types

| type | what counts | examples |
|---|---|---|
| researcher | an author or named person/group | "Smith et al." |
| material | a physical material / sample / compound | "perovskite", "MAPbI3" |
| method | a technique, model, or algorithm | "LSTM", "DFT", "MD" |
| task | the problem/goal being addressed | "efficiency prediction" |
| metric | a measured/reported quantity | "PCE", "MAE", "RMSE" |
| conclusion | a claim the paper states as its result | "X outperforms Y" |

Rules:
- An entity must actually appear in the paper text. No background or common-sense
  concepts the paper never names.
- Keep the surface form verbatim, including linearized sub/superscripts and
  Greek letters as the input gives them. Do not reword.
- Every mention carries `source_id`, `paragraph_id`, `quote`, and `surface`.

## Relation types

| type | meaning | direction requirement |
|---|---|---|
| uses | a method/material/task is applied | source -> target (the user -> the used) |
| compares | two entities are compared | between the two, condition stated |
| outperforms | one beats another on a metric | winner -> loser, metric + condition stated |
| supports | one claim supports another | evidence -> claim |
| contradicts | one claim conflicts with another | between the two claims |
| proposes | a paper/researcher proposes a method/task | proposer -> proposed |

Rules:
- Only relations with direct textual support. `direct` = stated verbatim;
  `inferred` = clearly implied by the text.
- Co-occurrence, review paraphrase, and speculation are NOT evidence — exclude
  them, or mark `strength: none` and keep them out of `edges`.
- A relation must state its condition (e.g. "at 300 K", "on dataset D").
- Never merge the two papers' conditions, samples, or numeric results into one
  relation claim.

## Evidence record (per node mention and per edge)

```json
{"source_id": "primary", "paragraph_id": "p3",
 "quote": "perovskite absorber", "strength": "direct"}
```

- `source_id` = `primary` or `secondary` (from corpus-manifest order).
- `paragraph_id` = JATS paragraph id from the material file, never a PDF page.
- `quote` = short verbatim excerpt.
- `strength` = `direct` | `inferred` (edge evidence only).
