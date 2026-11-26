#!/usr/bin/env python3
"""Assemble result.json for the paper-to-slides skill.

Usage:
  python write_result.py --outline outline.json --case case.json \
      --out /app/output/result.json \
      [--output-contract '{"field":"value",...}']

Behavior:
  - Merges every output_contract field (passed as JSON, normally copied
    verbatim from /input/task.md) with the outline's case_id and an honest
    status/sources/uncertainty/change_log block.
  - Never invents missing fields: absent keys stay absent and are listed in
    a "missing" note only if you pass --missing.
"""

import argparse
import json
import sys

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", required=True)
    ap.add_argument("--case", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--output-contract", default="{}", help="JSON object of output_contract fields")
    ap.add_argument("--status", default="partial")
    ap.add_argument("--uncertainty", action="append", default=[])
    ap.add_argument("--change-log", action="append", default=[])
    args = ap.parse_args(argv)

    with open(args.outline, "r", encoding="utf-8-sig") as f:
        outline = json.load(f)

    case = {}
    if args.case:
        try:
            with open(args.case, "r", encoding="utf-8-sig") as f:
                case = json.load(f)
        except Exception as e:  # noqa: BLE001
            case = {"case_file_error": str(e)}

    try:
        contract = json.loads(args.output_contract)
    except Exception:  # noqa: BLE001
        contract = {"output_contract_parse_error": args.output_contract[:200]}

    result = dict(contract)
    result.setdefault("case_id", outline.get("case_id") or case.get("case_id"))
    result["status"] = args.status
    result["sources"] = {
        "paper_title": outline.get("paper_title"),
        "case_file": args.case,
        "outline_file": args.outline,
    }
    result["uncertainty"] = list(args.uncertainty)
    result["change_log"] = list(args.change_log)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": args.out, "case_id": result.get("case_id"),
                      "status": result["status"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
