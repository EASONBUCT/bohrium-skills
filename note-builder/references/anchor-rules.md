# Evidence anchoring rules

Every note, finding, and knowledge point must be traceable back to a specific
place in the paper — not a loose "see the paper".

## Anchor record

```json
{"section": "Methods", "page": 3, "paragraph_id": "p7", "quote": "..."}
```

- `section` — the paper's own section heading where the claim appears.
- `page` — the PDF page number when the source is a PDF; omit when the source is
  paragraph-indexed and use `paragraph_id` instead. Never invent a page number.
- `quote` — a short verbatim excerpt. Short enough to check, long enough to
  identify the sentence.

## Granularity matches claim strength

- A direct finding → anchor to the exact sentence/paragraph + quote.
- A summary of a section → anchor to the section + one representative quote.
- A paper-level claim (e.g. the research question) → anchor to the section where
  it is stated.
- `未报告` / `无法判断` → no anchor; record the absence explicitly.

## Rules

- The quote must be verbatim (including linearized sub/superscripts and Greek
  letters as the input gives them).
- Do not cite a page/paragraph for a claim that is not there.
- A table or figure claim anchors to the figure/table caption and its location.
- Keep `uncertainty` when an anchor is approximate (e.g. OCR'd page).
