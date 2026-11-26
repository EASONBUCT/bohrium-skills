# Failure handling decision tree

Record each failure in `result.json.uncertainty` or `change_log`, produce what is
honestly available, and continue. Never fabricate paper content, a node, an edge,
a score, or a tool log.

## Corpus problems

- **Missing manifest / material files** → partial graph from what exists; state
  which source is missing.
- **Empty or truncated paper text** → extract only what is present; never fill
  gaps.
- **Root metadata confusion** → the first manifest entry is `primary`; never apply
  its DOI/title/authors to the second paper.
- **Linearized formulas / sub-superscripts** → quote them verbatim; check
  `secondary-publisher.xml` only to disambiguate, never to add values. No image
  pixels, supplementary attachments, or underlying clinical/experimental data —
  do not infer numbers from them.

## Extraction problems

- **Entity not actually in the text** → drop it; a model's background knowledge is
  not an entity.
- **Co-occurrence / review paraphrase / speculation presented as a relation** →
  exclude, or mark `strength: none` and keep out of `edges`.
- **Relation direction unclear** → record `direction: unknown` and mark
  `uncertainty`, do not guess a direction.
- **Same generic term, different object** → keep separate nodes + a conflict entry,
  never merge by surface string alone.

## Alignment problems

- **Alias ambiguity** → keep separate nodes + conflict, do not guess-merge.
- **Conflicting relations between the two papers** → keep both edges, mark
  `uncertainty: "conflict"`, do not drop one silently.

## Query problems

- **Query returns nothing** → report the empty result honestly with the query text;
  never invent matches.
- **Unknown query type** → the script returns an `error` field; fix the query, do
  not hardcode an answer.

## Budget problems

- Save `graph.json` first (deterministic, cheap). If time runs out, write
  `result.json` with `status: partial` from the graph built so far — it still
  carries full `source_id` + `paragraph_id` + quote evidence.
