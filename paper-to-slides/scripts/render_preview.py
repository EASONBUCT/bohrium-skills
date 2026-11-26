#!/usr/bin/env python3
"""Render a slide deck to PDF and per-page PNG previews.

Usage:
  python render_preview.py --deck deck.pptx --out preview_dir [--format pdf,png]

Behavior:
  - PPTX -> PDF via LibreOffice headless (soffice).
  - PDF -> per-page PNG via pdftoppm.
  - Writes preview_dir/deck.pdf and preview_dir/page_01.png ... .
  - Reports each stage honestly; a failed stage is recorded, not fabricated.
Exit 0 when at least the source deck exists; nonzero when the deck is missing.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return None, "", "tool not found"
    except Exception as e:  # noqa: BLE001
        return None, "", str(e)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if not os.path.exists(args.deck):
        print(json.dumps({"error": "deck missing", "deck": args.deck}))
        return 1

    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.deck))[0]
    pdf_path = os.path.join(args.out, base + ".pdf")
    report = {"deck": args.deck, "pdf": pdf_path, "pages": []}

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        code, out, err = run([soffice, "--headless", "--convert-to", "pdf",
                              "--outdir", args.out, args.deck])
        if code == 0 and os.path.exists(pdf_path):
            report["pdf_status"] = "ok"
        else:
            report["pdf_status"] = "failed"
            report["pdf_error"] = (err or out or "").strip()[:500]
    else:
        report["pdf_status"] = "skipped"
        report["pdf_error"] = "soffice/libreoffice not found"

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm and os.path.exists(pdf_path):
        prefix = os.path.join(args.out, "page")
        code, out, err = run([pdftoppm, "-png", "-r", "120", pdf_path, prefix])
        if code == 0:
            for f in sorted(os.listdir(args.out)):
                if f.startswith("page") and f.endswith(".png"):
                    report["pages"].append(os.path.join(args.out, f))
            report["png_status"] = "ok"
        else:
            report["png_status"] = "failed"
            report["png_error"] = (err or out or "").strip()[:500]
    else:
        report["png_status"] = "skipped"
        if not os.path.exists(pdf_path):
            report["png_error"] = "no PDF to rasterize"

    print(json.dumps(report, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
