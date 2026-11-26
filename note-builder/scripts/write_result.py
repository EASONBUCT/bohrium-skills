#!/usr/bin/env python3
"""Assemble result.json for the note-builder skill.

Usage:
  python write_result.py --notes notes.json --case case.json \
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
    ap.add_argument("--notes", required=True)
    ap.add_argument("--case", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--output-contract", default="{}")
    ap.add_argument("--status", default="partial")
    ap.add_argument("--uncertainty", action="append", default=[])
    ap.add_argument("--change-log", action="append", default=[])
    args = ap.parse_args(argv)

    notes = load_json(args.notes, {})
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
        "notes_file": args.notes,
    }
    result["uncertainty"] = list(args.uncertainty)
    result["change_log"] = list(args.change_log)
    result["notes"] = {
        "paper_card": notes.get("paper_card", {}),
        "sections": notes.get("sections", []),
        "knowledge_points": notes.get("knowledge_points", []),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "case_id": result.get("case_id"),
                      "status": result["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
