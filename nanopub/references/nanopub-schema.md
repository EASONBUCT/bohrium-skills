# Nanopublication schema

A nanopublication = one assertion + its evidence + source metadata + publication
info. Each part is a first-class field; nothing is packed into a single blob.

## Assertion

```json
{"subject": "LSTM", "predicate": "outperforms", "object": "baseline",
 "condition": "on the 2019 test split", "scope": "single dataset"}
```

- `subject` — the entity the claim is about (a method, material, task, metric, ...).
- `predicate` — a controlled relation (see below).
- `object` — the entity the subject relates to.
- `condition` — the precondition that makes the assertion true; a bare comparison
  without its condition is incomplete.
- `scope` — how far the claim reaches (single dataset / study / review).

## Controlled relation vocabulary (predicate)

| predicate | meaning |
|---|---|
| improves | subject beats object on a stated metric |
| uses | subject applies/employs object |
| measures | subject quantifies object |
| supports | subject provides evidence for object |
| contradicts | subject conflicts with object |
| equals | subject is the same as object (aliases/normalization) |
| produces | subject yields object |
| causes | subject leads to object (causal claim) |

Use the closest term; if none fits, use a literal lowercase predicate and note it
in `quality`.

## Evidence

```json
[{"quote": "LSTM outperformed the baseline on the 2019 test split",
  "location": "p14", "strength": "direct"}]
```

- `quote` — minimal sufficient verbatim fragment.
- `location` — page number (PDF) or `paragraph_id` (paragraph-indexed input); never invent.
- `strength` — `direct` (stated) | `inferred` (clearly implied). A review
  paraphrase or co-occurrence is not evidence.

## Source metadata (provenance)

Paper `title`, `authors`, `year`, `version`, `doi`, `data_source`, as they appear.
Missing → `未报告`; never guess a DOI or year.

## Publication info

Who asserted it (`asserted_by`), `timestamp`, `license`, and `version`. These
describe the nanopublication itself, not the paper.

## Confidence

`{"basis": "stated in Results", "value": "high|medium|low"}`. The basis is a
verifiable reason, not a number pulled from nowhere.
