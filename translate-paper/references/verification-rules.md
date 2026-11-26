# Translation verification rules ("关系准" / "可核验")

For each translated paragraph, check against the source and record the result in
`verification`:

- **numbers** — values, precision, ranges, and decimal separators unchanged.
- **units** — `nm`, `°C`, `%`, `mol/L` kept verbatim or rendered by the target
  language's convention without changing the value.
- **formulas** — math environments, symbols, sub/superscripts kept verbatim.
- **figure/table numbers** — `Fig. 3`, `Table 1` and their references unchanged.
- **citation markers** — `[12]`, `(Smith et al., 2020)` unchanged; the cited claim
  still cites the same work.
- **negation** — "not all", "no significant difference" keep their scope.
- **limitation / cause / concession** — "although", "because", "unless" keep their
  logical direction.

## Unclear handling

A part whose translation you cannot verify (ambiguous term, unparseable formula,
image-only table) goes into `unclear` with the `para_id` and a note — it is not
silently rendered. A provisional rendering is allowed only if it is listed in
`unclear`.
