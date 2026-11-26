# Template constraints and layout adaptation

The organizer provides a master/layout-based editable template (`.pptx` or `.potx`), and possibly a starting deck. The skill must adapt to it without destroying its identity.

## What to preserve

- **Masters and layouts** — add slides from the template's own slide layouts; do not rebuild a blank deck when a template is supplied.
- **Theme colors and fonts** — inherit them; do not override with hard-coded colors.
- **Footer / page number / logo placeholders** — leave them as the master defines.
- **Aspect ratio** — keep the template's slide size (16:9 vs 4:3); do not change it.

## Layout picking

- Use the layout whose placeholder structure matches the page type (title, section header, title+content, picture-with-caption).
- If a required layout is missing, fall back to the master's blank layout and add minimal text boxes, but keep the theme.
- Do not fill a subtitle-only placeholder with a long claim; put the claim in the title placeholder and the detail in the body.

## Fonts and text sizing

- Prefer the template's own fonts. If a glyph is missing (e.g., CJK), run font-discovery and fall back to a sans/serif pair that covers the script; record the substitution in `change_log`.
- Title ≥ 18 pt, body ≥ 12 pt (larger when the template implies it). Shrink only as a last resort.
- Never let text overflow its placeholder silently: the script flags truncated bullets in its `warnings`.

## Long content

- Long titles → shorten the claim, keep the verbatim phrase in the evidence `quote`.
- Many bullets → cut to the top 5 by evidential weight; move the rest to the speaker note.
- Multiple figures → at most 2 per page, side by side, with a shared caption line.

## Starting deck edit/adapt

When the case gives a starting deck that must be edited, load that deck (not a fresh template), replace or add only the required slides, and keep untouched slides as-is.
