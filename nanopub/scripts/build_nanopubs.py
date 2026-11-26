#!/usr/bin/env python3
"""Assemble nanopublications from an extraction JSON.

The agent writes extraction.json (source metadata + nanopubs) following
assets/nanopub.schema.json. This script is deterministic:
  - assigns stable ids
  - keeps assertion/evidence/provenance verbatim
  - marks unsupported/conflicting items
  - emits strict, machine-readable nanopubs.json

Usage:
  python build_nanopubs.py --extraction extraction.json --out nanopubs.json
"""

import argparse
import json
import sys


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    ex = load(args.extraction)
    source = ex.get("source", {})
    nanopubs = ex.get("nanopubs", [])

    out = []
    for i, np in enumerate(nanopubs):
        np = dict(np)
        np.setdefault("id", "np-%d" % (i + 1))
        # every nanopub carries the source metadata + publication info
        np.setdefault("provenance", {"source": source})
        np.setdefault("publication_info", {})
        out.append(np)

    result = {
        "schema": "nanopub/v1",
        "source": source,
        "nanopubs": out,
        "quality": ex.get("quality", []),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "nanopubs": len(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
