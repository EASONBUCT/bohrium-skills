#!/usr/bin/env python3
"""Assemble a bilingual translation from an extraction JSON.

The agent writes extraction.json (terminology, segments, verification, unclear)
following assets/translation.schema.json. This script is deterministic:
  - deduplicates terminology by normalized source term
  - flags segments missing a translation or para_id
  - emits translation.json

Usage:
  python build_translation.py --extraction extraction.json --out translation.json
"""

import argparse
import json
import re
import sys


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def norm(t):
    return re.sub(r"\s+", " ", (t or "").lower()).strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    ex = load(args.extraction)

    terms = ex.get("terminology", [])
    seen = set()
    term_out = []
    for t in terms:
        k = norm(t.get("source"))
        if k in seen:
            continue
        seen.add(k)
        term_out.append(t)

    segs = ex.get("segments", [])
    missing = [s.get("para_id", "?") for s in segs if not s.get("translation")]

    result = {
        "schema": "translate-paper/v1",
        "source_language": ex.get("source_language", ""),
        "target_language": ex.get("target_language", ""),
        "terminology": term_out,
        "segments": segs,
        "untranslated_segments": missing,
        "verification": ex.get("verification", []),
        "unclear": ex.get("unclear", []),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "terms": len(term_out),
                      "segments": len(segs), "untranslated": missing},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
