---
name: paper-to-slides
description: Convert a research paper (PDF) plus an organizer-provided slide template into an editable, template-compliant academic slide deck with one-claim-per-page structure, figure/table/equation/section evidence mapping, non-duplicative speaker notes, and real rendered PDF/PNG previews. Use when a case provides a paper under /input plus a slide template and asks for an academic presentation deliverable whose result.json must echo the case task.md output_contract fields under /app/output. Do not use for creating new scientific figures, polishing prose, or writing the paper itself.
---

# Paper → Academic Slides

Turn one research paper into an editable, presentable academic deck that keeps, for every page, a traceable link back to the paper's figure / table / equation / section / data. The output is not "paragraphs cut into slides"; it is a claim-first rewrite that stays faithful to the paper's own contribution.

## Runtime contract (authoritative)

- Read the real inputs under `/input/case.json` and `/input/task.md`. `task.md` declares the `output_contract` fields that `result.json` must echo. The paper PDF is provided as material; read the actual file, never trust filenames or labels.
- Work in `/app/work` (scratch). Final artifacts go under `/app/output`.
- `/app/output/result.json` must contain **every** original `output_contract` field from `task.md`, plus `case_id`, `status`, `sources`, `uncertainty`, and `change_log`. Missing, undecidable, and failed parts are stated explicitly — never fabricated.
- Every editable slide/office artifact must have a real rendered PDF/PNG preview for inspection.
- Budgets: roughly 64 model requests, 900 s, 16384 tokens per response. Save partial deliverables early and improve incrementally.
- Do not invent benchmark scores, run logs, software state, or scientific data. A partial result names its limits.

## Inputs to collect first

1. `/input/case.json` — `case_id`, paper path, template path, audience, time budget, slide-count cap, and any per-case constraints.
2. `/input/task.md` — the exact `output_contract` fields and completion criteria.
3. The paper PDF — resolve from `case.json`, then `task.md`, then by searching `/input` recursively. If still absent, record the gap and continue on what exists.

## Procedure (in order)

### 1. Read the case
Record `case_id`, paper path, template path, audience, time, `max_slides`, and the `output_contract` field names. Write them into a scratch notes file under `/app/work`.

### 2. Parse the paper
- Extract text with `pdftotext -layout` (pdf-text-tool). Render pages with `pdftoppm` (pdf-render-tool) for figure extraction and later cropping.
- Build a **figure/table/equation inventory**: `{ref: "Fig. 3", kind: figure|table|equation|scheme, page: int, caption: "...", data_or_illustration: experimental|schematic|computed}`.
- If text is empty (scanned PDF), run OCR and record the method in `uncertainty`.
- Transcribe numbers, units, method names, and conclusion wording verbatim; never re-round or reword a measured value.

### 3. Extract the mainline (claim-first, not paragraph-order)
Produce the narrative skeleton and store it in the outline's `narrative` block:
- research question / gap → core approach (method) → key evidence (grouped, each tied to a figure/table) → conclusion → limitations.
- Rules: separate the paper's own contribution from background and prior work; never present a schematic as experimental data; keep the paper's own conclusion separate from the authors' discussion of other work. Detail in `references/mainline-extraction.md`.

### 4. Design the page-level outline
One page = one claim. For each page record: `claim`, `bullets` (≤5 short phrases), `evidence` (refs), `transition`, `speaker_note`, `layout`, and optional `image`. Follow `references/page-structure.md` for density, phrasing, and overflow rules. Validate against `assets/outline.schema.json`.

### 5. Write speaker notes
Each note must **not** repeat the page text. It must carry (a) the transition in, (b) the emphasis point, and (c) 1–2 backup evidence items for likely questions. See `references/evidence-mapping.md`.

### 6. Generate the editable deck
```
python scripts/build_pptx.py --outline /app/work/outline.json \
  --template /input/<template>.pptx \
  --out /app/output/deck.pptx --max-slides N
```
The script prefers `python-pptx` (preserves the template's masters, layouts, theme colors, footer, fonts); if `python-pptx` is unavailable it falls back to a dependency-free OOXML writer that still produces an openable, editable deck, and reports which path it used. Ensure `python-pptx` is installed when the template must be preserved exactly (`pip install python-pptx`).

### 7. Render previews
```
python scripts/render_preview.py --deck /app/output/deck.pptx --out /app/output/preview
```
Converts to PDF via LibreOffice (`soffice --headless --convert-to pdf`), then PDF → per-page PNG via `pdftoppm`. On failure, keep the source deck and record the renderer error.

### 8. Build evidence map and result.json
- `scripts/build_pptx.py` also writes `/app/output/evidence_map.json` (page → claim → evidence refs), matching `assets/evidence-map.schema.json`.
- `scripts/write_result.py` assembles `/app/output/result.json` from the outline, case metadata, and an honest status/sources/uncertainty/change_log you supply.

## Output layout under /app/output

- `deck.pptx` — editable deck (organizer-required filename, if any, takes precedence).
- `evidence_map.json` — page-level evidence mapping.
- `preview/deck.pdf`, `preview/page_01.png`, … — real renders.
- `result.json` — `output_contract` fields + `case_id` + `status` + `sources` + `uncertainty` + `change_log`.

## Definition of done (check each before writing result.json)

- [ ] Mainline matches the paper's own contribution, not paragraph order.
- [ ] Every page traces to a specific paper figure/table/equation/section/page.
- [ ] Numbers, units, method names, and conclusion wording match the paper.
- [ ] No schematic is presented as experimental data.
- [ ] Speaker notes exist and do not duplicate page text.
- [ ] The deck opens, plays, and is editable; previews render.
- [ ] `result.json` includes every `output_contract` field + `case_id` + honest status/sources/uncertainty/change_log.

## Failure handling (top rules)

Full decision tree in `references/exception-handling.md`. Headlines:
- Encrypted/unreadable PDF → record, produce a partial result from whatever is extractable (e.g., abstract); never invent content.
- Equations rendered as images / formulas lost → keep the verbatim image or LaTeX from the paper and mark `uncertainty`.
- Template placeholders insufficient → add minimal slides from the master's blank layout; never overwrite theme colors or footer.
- Fonts missing → run font-discovery, prefer template-embedded fonts, fall back to a sans/serif pair and record the change.
- Slide-count exceeded → merge support pages while keeping one-claim-per-page; record the compression in `change_log`.
- Rendering fails → keep the source deck, record the renderer error; mark previews as missing.

## Resources

- `references/page-structure.md` — density, bullet phrasing, overflow rules.
- `references/mainline-extraction.md` — narrative-skeleton extraction.
- `references/evidence-mapping.md` — evidence-map schema and citation rules.
- `references/template-constraints.md` — master/layout/font/footer rules.
- `references/exception-handling.md` — full failure decision tree.
- `assets/outline.schema.json`, `assets/evidence-map.schema.json` — schemas.
- `scripts/build_pptx.py`, `scripts/render_preview.py`, `scripts/write_result.py`.

## Minimal example (illustrative — not a formal case answer)

Input `outline.json` (synthetic one-slide example, marked 示例):

```json
{"case_id": "example-001", "paper_title": "示例：一种合金的热导率",
 "audience": "领域同行", "time_minutes": 5, "max_slides": 3,
 "narrative": {"question": "合金热导率随温度如何变化", "approach": "MD + 实验校验",
   "key_results": ["300–700K 内热导率单调下降"], "conclusion": "声子散射主导", "limitations": ["未考虑晶界"]},
 "slides": [
   {"index": 1, "claim": "该合金热导率在 300–700 K 单调下降（示例，非正式案例）",
    "bullets": ["MD 预测 12.3→8.1 W/m·K", "实验在 5% 内一致"],
    "evidence": [{"ref": "Fig. 3", "kind": "figure", "page": 5, "caption": "温度-热导率曲线"}],
    "transition": "从问题进入结果", "speaker_note": "先指出趋势，再强调与实验一致，若被问到低温行为引用 Fig. 2 的补充数据。",
    "layout": "bullets_figure"}]
}
```

Call: `python scripts/build_pptx.py --outline outline.json --out deck.pptx` then
`python scripts/render_preview.py --deck deck.pptx --out preview`.
Sample output (示意): `deck.pptx` (3 slides), `preview/deck.pdf`, `preview/page_01.png`, and `result.json` echoing `output_contract` fields.
