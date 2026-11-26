# Evidence mapping and speaker notes

## Evidence map (per page)

Each slide records, for every claim, the paper location(s) that support it:

- `ref` — the figure/table/equation label or section heading (e.g., "Fig. 3", "Table 2", "§3.2").
- `kind` — one of `figure | table | equation | section | data`.
- `page` — the paper page (integer) where it appears.
- `caption` — verbatim figure/table caption (or a truncated first sentence with "…").
- `quote` — the verbatim supporting sentence, truncated if long.

Rules:
- A claim with no evidence ref is not a finished page: either find the source or demote it to a section/transition page.
- A figure reference must match the figure actually described in the text; do not cross-wire figure numbers across pages.
- Keep units, axis labels, and condition notes (e.g., "300 K", "vs. OER", "n = 5") with the reference so a reviewer can locate it.

## Speaker notes (must not repeat the page)

For each page write a note containing:

1. **Transition** — one sentence linking the previous page to this one.
2. **Emphasis** — what the audience should notice first on this slide.
3. **Backup evidence** — 1–2 additional paper facts to answer a likely question ("what about low temperature? cf. Fig. 2").

Anti-patterns to avoid:
- Do not restate the bullets. The note is a prompt for the speaker, not a script of the slide.
- Do not invent numbers in the note that are absent from the paper.
- If a page is a transition/section page, the note states what the next block will establish.
