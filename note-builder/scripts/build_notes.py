#!/usr/bin/env python3
"""Assemble structured notes from an extraction JSON.

The agent writes extraction.json (paper_card, sections, knowledge_points)
following assets/note.schema.json. This script is deterministic:
  - deduplicates knowledge points by normalized label
  - assigns stable ids
  - keeps anchors verbatim
  - emits notes.json

Usage:
  python build_notes.py --extraction extraction.json --out notes.json
"""

import argparse
import json
import re
import sys


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def norm(label):
    s = (label or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    ex = load(args.extraction)
    paper_card = ex.get("paper_card", {})
    sections = ex.get("sections", [])
    kps = ex.get("knowledge_points", [])

    # dedup knowledge points by normalized label; keep first, merge anchors
    seen = {}
    kp_out = []
    for kp in kps:
        key = norm(kp.get("label"))
        if key in seen:
            seen[key].setdefault("anchors", []).extend(kp.get("anchors", []))
            continue
        kp = dict(kp)
        kp.setdefault("id", "kp-%d" % (len(kp_out) + 1))
        seen[key] = kp
        kp_out.append(kp)

    for i, s in enumerate(sections):
        s.setdefault("id", "sec-%d" % (i + 1))

    notes = {
        "schema": "note-builder/v1",
        "paper_card": paper_card,
        "sections": sections,
        "knowledge_points": kp_out,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "sections": len(sections),
                      "knowledge_points": len(kp_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
