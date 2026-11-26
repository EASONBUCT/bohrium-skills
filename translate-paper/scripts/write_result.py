#!/usr/bin/env python3
"""Assemble result.json for the translate-paper skill.

Usage:
  python write_result.py --translation translation.json --case case.json \
      --out /app/output/result.json \
      [--output-contract '{"field":"value",...}'] \
      [--status complete|partial|failed] \
      [--uncertainty "..."] [--change-log "..."]

Merges every output_contract field (copied verbatim from task.md) with case_id
and an honest status/sources/uncertainty/change_log block.
"""

import argparse
import json
import sys


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        return default if default is not None else {"error": str(e)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--translation", required=True)
    ap.add_argument("--case", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--output-contract", default="{}")
    ap.add_argument("--status", default="partial")
    ap.add_argument("--uncertainty", action="append", default=[])
    ap.add_argument("--change-log", action="append", default=[])
    args = ap.parse_args(argv)

    tr = load_json(args.translation, {})
    case = load_json(args.case, {}) if args.case else {}

    try:
        contract = json.loads(args.output_contract)
    except Exception:  # noqa: BLE001
        contract = {"output_contract_parse_error": args.output_contract[:200]}

    result = dict(contract)
    result.setdefault("case_id", case.get("case_id"))
    result["status"] = args.status
    result["sources"] = {
        "case_file": args.case,
        "translation_file": args.translation,
    }
    result["uncertainty"] = list(args.uncertainty)
    result["change_log"] = list(args.change_log)
    result["translation"] = {
        "source_language": tr.get("source_language", ""),
        "target_language": tr.get("target_language", ""),
        "terminology": tr.get("terminology", []),
        "segments": tr.get("segments", []),
        "verification": tr.get("verification", []),
        "unclear": tr.get("unclear", []),
        "untranslated_segments": tr.get("untranslated_segments", []),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "case_id": result.get("case_id"),
                      "status": result["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
