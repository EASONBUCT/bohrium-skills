# Note fields and section rules

## Paper card fields

| field | what it holds | required-ness |
|---|---|---|
| title | the paper's own title | verbatim |
| authors | authors as listed | verbatim |
| research_question | the question/objective the paper states | extract; `未报告` if absent |
| data | samples, datasets, sources, and their scope | extract; `未报告` if absent |
| methods | techniques/models, with their conditions | extract |
| conditions | the preconditions a finding depends on (temperature, dataset, split, etc.) | extract; keep attached to the finding |
| main_findings | the paper's stated results | extract; one per claim, keep the condition |
| limitations | limits the paper itself states | extract; `未报告` if the paper states none |

Rules:
- Use the paper's own wording for values and numbers; do not reword or re-round.
- A finding without its condition is incomplete: record the condition in the same
  item (e.g. "LSTM outperformed baseline — condition: on the 2019 test split").
- Distinguish the paper's own claim from its report of others' work.
- Never fill a missing field from general background knowledge — mark `未报告`.

## Section rules

- Mirror the paper's actual heading titles and order. Do not force
  Introduction/Methods/Results/Discussion if the paper uses other headings.
- Each section: `id`, `title` (verbatim heading), `summary` (purpose, method,
  result, conclusion as the paper presents them), and `anchors`.
- Preserve the linking between sections (what the paper carries forward).

## Knowledge point types

| type | examples |
|---|---|
| concept | a defined term/idea the paper introduces or uses |
| variable | a quantity, symbol, or parameter |
| method | a technique, model, algorithm, or protocol |
| conclusion | a claim the paper states as its result |

Rules:
- One retrievable entry per concept/variable/method/conclusion.
- Normalize aliases and abbreviations; record the alias list instead of making
  duplicate entries.
- A conflict between two of the paper's own statements stays as two entries with
  an `uncertainty: "conflict"` note — never silently merged.
- Each entry carries anchors (section + page/paragraph + quote).
