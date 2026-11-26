#!/usr/bin/env python3
"""Build an editable .pptx deck from a deck-outline JSON.

Usage:
  python build_pptx.py --outline outline.json [--template template.pptx] \
      --out deck.pptx [--max-slides N] [--evidence-map evidence_map.json]

Behavior:
  - Loads the outline JSON (see assets/outline.schema.json).
  - Prefers python-pptx (preserves the template's masters/layouts/theme/footer).
  - Falls back to a dependency-free minimal OOXML writer when python-pptx is
    not importable, so the deck is still openable and editable.
  - Writes the deck, and (by default) an evidence_map.json next to --out.
  - Prints a one-line JSON summary and exits 0 on success, 1 on failure.
"""

import argparse
import json
import os
import sys

def load_outline(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def derive_evidence_map(outline):
    slides = []
    for s in outline.get("slides", []):
        slides.append({
            "index": s.get("index"),
            "claim": s.get("claim", ""),
            "evidence": s.get("evidence", []),
            "speaker_note": s.get("speaker_note", ""),
        })
    return {
        "case_id": outline.get("case_id"),
        "paper_title": outline.get("paper_title"),
        "slides": slides,
    }

def build_with_python_pptx(outline, template_path, out_path, max_slides, warnings):
    from pptx import Presentation
    from pptx.util import Pt

    prs = Presentation(template_path) if template_path and os.path.exists(template_path) \
        else Presentation()

    slides = outline.get("slides", [])
    if max_slides and len(slides) > max_slides:
        slides = slides[:max_slides]
        warnings.append("truncated to max_slides=%d" % max_slides)

    # Layout indices: 0=title, 1=title+content, 5=title only, 6=blank (typical).
    layouts = prs.slide_layouts
    for s in slides:
        layout_key = s.get("layout", "bullets")
        if layout_key == "title" and len(layouts) > 0:
            layout = layouts[0]
        elif layout_key in ("section",) and len(layouts) > 6:
            layout = layouts[6]
        elif len(layouts) > 1:
            layout = layouts[1]
        else:
            layout = layouts[0]

        slide = prs.slides.add_slide(layout)

        # Title
        if slide.shapes.title is not None:
            slide.shapes.title.text = s.get("claim", "")

        # Body bullets: fill the first body placeholder found.
        body = None
        for ph in slide.placeholders:
            if ph.placeholder_format.idx == 1:
                body = ph
                break
        if body is not None:
            tf = body.text_frame
            tf.clear()
            bullets = s.get("bullets", [])
            for i, b in enumerate(bullets[:6]):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = b
                p.level = 0

        # Optional figure image.
        img = s.get("image")
        if img and os.path.exists(img):
            try:
                slide.shapes.add_picture(img, 0, 0)
            except Exception as e:  # noqa: BLE001
                warnings.append("image insert failed slide %s: %s" % (s.get("index"), e))

        # Speaker notes.
        note = s.get("speaker_note")
        if note and slide.has_notes_slide:
            slide.notes_slide.notes_text_frame.text = note

    prs.save(out_path)
    return "python-pptx"

def _xml(tag, attrs=None, text=None):
    a = ""
    if attrs:
        a = "".join(' %s="%s"' % (k, str(v).replace("&", "&amp;").replace('"', "&quot;")) for k, v in attrs.items())
    t = ""
    if text is not None:
        t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "<%s%s>%s</%s>" % (tag, a, t, tag)

def build_minimal_pptx(outline, out_path, max_slides, warnings):
    """Dependency-free, minimal but valid, editable PPTX (text-only)."""
    import zipfile

    slides = outline.get("slides", [])
    if max_slides and len(slides) > max_slides:
        slides = slides[:max_slides]
        warnings.append("truncated to max_slides=%d" % max_slides)

    title = outline.get("paper_title", "Deck")

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        + "".join('<Override PartName="/ppt/slides/slide%d.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' % (i + 1) for i in range(len(slides))) +
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )

    slide_refs = "".join(
        '<p:sldId id="%d" r:id="rId%d"/>' % (256 + i, i + 1) for i in range(len(slides)))
    pres_rel = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
        + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide%d.xml"/>' % (i + 1, i + 1) for i in range(len(slides))) +
        '</Relationships>'
    )

    pres = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" saveSubsetFonts="1">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        '<p:sldIdLst>%s</p:sldIdLst>'
        '<p:sldSz cx="12192000" cy="6858000" type="screen4x3"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        '</p:presentation>' % slide_refs
    )

    master = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '</p:spTree></p:cSld>'
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        '</p:sldMaster>'
    )
    master_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
        '</Relationships>'
    )

    layout = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="titleAndContent" preserve="1">'
        '<p:cSld name="Title and Content"><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        # Title placeholder
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="457200" y="274638"/><a:ext cx="11277600" cy="1143000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t></a:t></a:r></a:p></p:txBody></p:sp>'
        # Body placeholder
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="457200" y="1600200"/><a:ext cx="11277600" cy="5029200"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t></a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld>'
        '<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>'
        '</p:sldLayout>'
    )
    layout_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
        '</Relationships>'
    )

    theme = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
        '<a:themeElements><a:clrScheme name="Office">'
        '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="1F497D"/></a:dk2>'
        '<a:lt2><a:srgbClr val="EEECE1"/></a:lt2>'
        '<a:accent1><a:srgbClr val="4F81BD"/></a:accent1>'
        '<a:accent2><a:srgbClr val="C0504D"/></a:accent2>'
        '<a:accent3><a:srgbClr val="9BBB59"/></a:accent3>'
        '<a:accent4><a:srgbClr val="8064A2"/></a:accent4>'
        '<a:accent5><a:srgbClr val="4BACC6"/></a:accent5>'
        '<a:accent6><a:srgbClr val="F79646"/></a:accent6>'
        '<a:hlink><a:srgbClr val="0000FF"/></a:hlink>'
        '<a:folHlink><a:srgbClr val="800080"/></a:folHlink>'
        '</a:clrScheme>'
        '<a:fontScheme name="Office">'
        '<a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
        '<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
        '</a:fontScheme>'
        '<a:fmtScheme name="Office">'
        '<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
        '<a:lnStyleLst><a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst>'
        '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
        '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
        '</a:fmtScheme>'
        '</a:themeElements></a:theme>'
    )

    def slide_xml(s):
        claim = s.get("claim", "")
        bullets = s.get("bullets", [])[:6]
        bparas = ""
        for b in bullets:
            bparas += '<a:p><a:r><a:rPr lang="en-US" sz="1800"/><a:t>%s</a:t></a:r></a:p>' % b.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            # Title textbox (inherits layout title placeholder look)
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="457200" y="274638"/><a:ext cx="11277600" cy="1143000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            '<p:txBody><a:bodyPr/><a:lstStyle/>'
            '<a:p><a:r><a:rPr lang="en-US" sz="2400" b="1"/><a:t>%s</a:t></a:r></a:p>'
            '</p:txBody></p:sp>'
            # Body textbox
            '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="457200" y="1600200"/><a:ext cx="11277600" cy="5029200"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            '<p:txBody><a:bodyPr/><a:lstStyle/>%s</p:txBody></p:sp>'
            '</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>'
            '</p:sld>'
        ) % (claim.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), bparas)

    def slide_rels(i):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
            '</Relationships>'
        )

    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>%s</dc:title><cp:lastModifiedBy>paper-to-slides</cp:lastModifiedBy></cp:coreProperties>'
    ) % title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>paper-to-slides</Application><Slides>%d</Slides></Properties>' % len(slides)
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rel)
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        z.writestr("ppt/theme/theme1.xml", theme)
        for i, s in enumerate(slides):
            z.writestr("ppt/slides/slide%d.xml" % (i + 1), slide_xml(s))
            z.writestr("ppt/slides/_rels/slide%d.xml.rels" % (i + 1), slide_rels(i))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    return "stdlib-pptx"

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", required=True)
    ap.add_argument("--template", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-slides", type=int, default=None)
    ap.add_argument("--evidence-map", default=None)
    args = ap.parse_args(argv)

    outline = load_outline(args.outline)
    warnings = []

    try:
        import pptx  # noqa: F401
        backend = build_with_python_pptx(outline, args.template, args.out, args.max_slides, warnings)
    except ImportError:
        backend = build_minimal_pptx(outline, args.out, args.max_slides, warnings)
    except Exception as e:  # noqa: BLE001
        # python-pptx present but failed (e.g. template issue): fall back.
        warnings.append("python-pptx failed (%s); using stdlib fallback" % e)
        backend = build_minimal_pptx(outline, args.out, args.max_slides, warnings)

    emap_path = args.evidence_map or (os.path.splitext(args.out)[0] + "_evidence_map.json")
    with open(emap_path, "w", encoding="utf-8") as f:
        json.dump(derive_evidence_map(outline), f, ensure_ascii=False, indent=2)

    print(json.dumps({"backend": backend, "slides": len(outline.get("slides", [])),
                      "warnings": warnings, "out": args.out, "evidence_map": emap_path},
                     ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
