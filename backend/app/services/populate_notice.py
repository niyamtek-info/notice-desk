"""
populate_notice.py  —  13(2) SARFAESI notice filler
====================================================
Usage:
    python populate_notice.py \
        --template   notice_template.docx \
        --data       report_fields.json \
        --output     filled_notice.docx \
        --signature  /path/to/ao_signature.png   # optional

Changes:
  • To-section S.No numbering increments per co-borrower (2, 3, ...)
    since the borrower is always "1."
  • {{AO-Signature}} placeholder is replaced with an inline image drawn
    from the --signature PNG file (right-aligned, proportionally sized
    to fit the 6564 DXA wide cell at a reasonable signature height).
    If --signature is not supplied the placeholder is left blank as before.
"""

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


FALLBACK = "N/A"

# ── Formatting helpers ───────────────────────────────────────────────────────

def fmt_date(value):
    if not value:
        return FALLBACK
    try:
        return datetime.fromisoformat(str(value).strip()).strftime("%d-%m-%Y")
    except ValueError:
        return str(value).strip()


def fmt_amount(value):
    if value is None:
        return FALLBACK
    try:
        n = int(value)
        s = str(n)
        if len(s) <= 3:
            return s
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]
        return result.lstrip(",")
    except (ValueError, TypeError):
        return str(value)


def as_str(value, transform=None):
    if value is None:
        return FALLBACK
    s = str(value).strip() or FALLBACK
    return transform(s) if transform else s


def build_short_property_address(fields):
    for key in (
        "property_address",
        "mortgaged_property_address",
        "address_of_mortgaged_property",
    ):
        value = fields.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text

    parts = []
    for key in ("door_number", "property_street", "property_locality",
                "property_town", "taluk", "district", "pincode"):
        v = fields.get(key)
        if v:
            parts.append(str(v).strip())
    if parts:
        return ", ".join(parts)

    addr = fields.get("borrower_address")
    return addr.strip() if addr else "As per Schedule B"


# ── Placeholder mapping ──────────────────────────────────────────────────────

def build_mapping(fields):
    def f(key, transform=None): return as_str(fields.get(key), transform)
    def d(key): return fmt_date(fields.get(key))
    def amt(key): return fmt_amount(fields.get(key))
    return {
        "{{SEC_13_2_NOTICE_DATE}}":      d("sec_13_2_notice_date"),
        "{{BORROWER_NAME}}":             f("borrower_name", str.upper),
        "{{ARC_NAME}}":                  f("arc_name"),
        "{{TRUST_NAME}}":                f("arc_name"),
        "{{ASSIGNOR_NAME}}":             f("arc_name"),
        "{{ASSIGNMENT_DATE}}":           d("loan_agreement_date"),
        "{{LOAN_ACCOUNT_NUMBER}}":       f("loan_account_number"),
        "{{LOAN_AMOUNT}}":               amt("loan_amount"),
        "{{LOAN_AMOUNT_WORDS}}":         f("loan_amount_words", str.upper),
        "{{LOAN_AGREEMENT_DATE}}":       d("loan_agreement_date"),
        "{{DATE_OF_NPA}}":               d("date_of_npa"),
        "{{AS_ON_DATE}}":                d("as_on_date"),
        "{{FCL_DATE}}":                  d("fcl_as_on_date"),
        "{{FCL_AMOUNT}}":                amt("total_outstanding"),
        "{{FCL_AMOUNT_WORDS}}":          f("total_outstanding_words", str.upper),
        "{{TOTAL_OUTSTANDING}}":         amt("total_outstanding"),
        "{{FUTURE_PRINCIPAL}}":          amt("future_principal"),
        "{{PRINCIPAL_OUTSTANDING}}":     amt("principal_outstanding"),
        "{{INSTALMENT_OVERDUE_AMOUNT}}": amt("instalment_overdue_amount"),
        "{{INTEREST_ON_TERMINATION}}":   amt("interest_on_termination"),
        "{{LATE_PAYMENT_PENALTY}}":      amt("late_payment_penalty"),
        "{{CHEQUE_BOUNCE_CHARGES}}":     amt("cheque_bounce_charges"),
        "{{OTHER_AMOUNT}}":              amt("other_amount"),
        "{{FORECLOSURE_CHARGES}}":       amt("foreclosure_charges"),
    }


# ── Borrower table (Table 1) ─────────────────────────────────────────────────

def fill_borrower_table(xml, fields):
    borrower_addr = (fields.get("borrower_address") or FALLBACK).strip()
    prop_addr     = build_short_property_address(fields)
    xml = xml.replace("&lt;Address of the Borrower&gt;", borrower_addr, 1)
    xml = xml.replace("&lt;Address of Mortgaged Property&gt;", prop_addr, 1)
    return xml


# ── Co-borrower block (Table 2) ──────────────────────────────────────────────
# The template's left-cell "S.No" becomes the sequential number (2, 3, ...)
# since the borrower row above it is always "1."

CO_BORROWER_BLOCK_RE = re.compile(
    r"(<w:tr\b[^>]*>(?:(?!<w:tr\b).)*?{{CO_BORROWER_NAME}}(?:(?!<w:tr\b).)*?</w:tr>)"
    r"(\s*<w:tr\b.*?</w:tr>)"
    r"(\s*<w:tr\b.*?</w:tr>)",
    re.DOTALL,
)

# Pattern to find "S.No" text inside a run — we'll replace it with the sequence number
SNO_TEXT_RE = re.compile(r'(<w:t[^>]*>)S\.No(</w:t>)')


def collect_co_borrowers(fields):
    result = []
    for i in range(1, 7):
        name = fields.get(f"co_borrower_{i}_name")
        addr = fields.get(f"co_borrower_{i}_address") or ""
        if name:
            result.append((name.strip().upper(), addr.strip()))
    return result


def handle_co_borrowers(xml, fields):
    match = CO_BORROWER_BLOCK_RE.search(xml)
    if not match:
        print("[WARN] Could not locate co-borrower block.", file=sys.stderr)
        return xml

    row1, row2, row3 = match.group(1), match.group(2), match.group(3)
    prop_addr    = build_short_property_address(fields)
    co_borrowers = collect_co_borrowers(fields)

    if not co_borrowers:
        replacement = ""
    else:
        blocks = []
        for idx, (name, addr) in enumerate(co_borrowers, start=1):
            # Sequence number in To section: borrower is 1, so co-borrowers start at 2
            seq_num = idx + 1

            r1 = row1.replace("{{CO_BORROWER_NAME}} (Co-Borrower No. )",
                              f"{name} (Co-Borrower No. {idx})")
            # Replace "S.No" in the number cell with the actual sequence number
            r1 = SNO_TEXT_RE.sub(rf'\g<1>{seq_num}.\g<2>', r1)

            r2 = row2.replace("&lt;Address of the Borrower&gt;", addr or FALLBACK)
            r3 = row3.replace("&lt;Address of Mortgaged Property&gt;", prop_addr)
            blocks.append(r1 + r2 + r3)
        replacement = "\n".join(blocks)

    return xml[: match.start()] + replacement + xml[match.end():]


def replace_placeholders(xml, mapping):
    for k, v in mapping.items():
        xml = xml.replace(k, v)
    return xml


# ── AO Signature image insertion ─────────────────────────────────────────────

def png_dimensions(png_path):
    """Read width, height in pixels from PNG using PIL (reliable across all PNGs)."""
    try:
        from PIL import Image
        img = Image.open(png_path)
        return img.size  # (width, height)
    except ImportError:
        pass
    # Fallback: read IHDR chunk directly
    with open(png_path, 'rb') as f:
        sig = f.read(8)
        if sig != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f"Not a valid PNG file: {png_path}")
        f.read(4)
        chunk_type = f.read(4)
        if chunk_type != b'IHDR':
            raise ValueError("PNG IHDR chunk not found")
        data = f.read(13)
        w = struct.unpack('>I', data[0:4])[0]
        h = struct.unpack('>I', data[4:8])[0]
    return w, h


def add_image_relationship(rels_path, image_rId, image_target):
    """Add an image relationship to a .rels file and return the file content."""
    with open(rels_path, encoding='utf-8') as f:
        rels = f.read()

    # Insert before </Relationships>
    new_rel = (f'  <Relationship Id="{image_rId}" '
               f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
               f'Target="{image_target}"/>')
    rels = rels.replace('</Relationships>', new_rel + '\n</Relationships>')

    with open(rels_path, 'w', encoding='utf-8') as f:
        f.write(rels)


def inline_image_xml(rId, cx_emu, cy_emu, img_id=1):
    """
    Return the XML for an inline (in-flow) image run.
    cx_emu, cy_emu: dimensions in English Metric Units (914400 EMU = 1 inch).
    """
    return (
        f'<w:r>'
        f'<w:rPr><w:noProof/></w:rPr>'
        f'<w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx_emu}" cy="{cy_emu}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{img_id}" name="AOSignature"/>'
        f'<wp:cNvGraphicFramePr>'
        f'<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        f'noChangeAspect="1"/>'
        f'</wp:cNvGraphicFramePr>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr>'
        f'<pic:cNvPr id="{img_id}" name="AOSignature"/>'
        f'<pic:cNvPicPr/>'
        f'</pic:nvPicPr>'
        f'<pic:blipFill>'
        f'<a:blip r:embed="{rId}"/>'
        f'<a:stretch><a:fillRect/></a:stretch>'
        f'</pic:blipFill>'
        f'<pic:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx_emu}" cy="{cy_emu}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'</pic:spPr>'
        f'</pic:pic>'
        f'</a:graphicData>'
        f'</a:graphic>'
        f'</wp:inline>'
        f'</w:drawing>'
        f'</w:r>'
    )


def insert_signature_image(xml, unpacked_dir, sig_png_path):
    """
    Replace {{AO-Signature}} text with an inline PNG image.

    Steps:
    1. Copy the PNG into word/media/ as signature.png
    2. Add a relationship entry in word/_rels/document.xml.rels
    3. Ensure 'png' is registered in [Content_Types].xml
    4. Replace the <w:t>{{AO-Signature}}</w:t> run with a <w:drawing> run
    """
    # ── 1. Copy image file ───────────────────────────────────────────────────
    media_dir  = os.path.join(unpacked_dir, "word", "media")
    os.makedirs(media_dir, exist_ok=True)
    dest_img   = os.path.join(media_dir, "signature.png")
    shutil.copy2(sig_png_path, dest_img)

    # ── 2. Add relationship ──────────────────────────────────────────────────
    rels_path  = os.path.join(unpacked_dir, "word", "_rels", "document.xml.rels")
    image_rId  = "rId99"   # use a high number unlikely to clash with existing rIds
    add_image_relationship(rels_path, image_rId, "media/signature.png")

    # ── 3. Register PNG content type (add only if not already present) ───────
    ct_path = os.path.join(unpacked_dir, "[Content_Types].xml")
    with open(ct_path, encoding='utf-8') as f:
        ct = f.read()
    if 'Extension="png"' not in ct:
        ct = ct.replace(
            '</Types>',
            '  <Default Extension="png" ContentType="image/png"/>\n</Types>'
        )
        with open(ct_path, 'w', encoding='utf-8') as f:
            f.write(ct)

    # ── 4. Calculate image dimensions ────────────────────────────────────────
    # Target display height: 1.5 cm  (a typical signature stamp height)
    # Keep aspect ratio from actual PNG pixel dimensions.
    TARGET_HEIGHT_CM = 1.5
    EMU_PER_CM       = 360000   # 914400 EMU/inch ÷ 2.54 cm/inch

    px_w, px_h = png_dimensions(sig_png_path)
    cy_emu = int(TARGET_HEIGHT_CM * EMU_PER_CM)
    cx_emu = int(cy_emu * px_w / px_h)

    # Cap width at cell width (6564 DXA → 6564 * 914400 / 1440 EMU)
    MAX_CX = int(6564 * 914400 / 1440)
    if cx_emu > MAX_CX:
        cx_emu = MAX_CX
        cy_emu = int(cx_emu * px_h / px_w)

    # ── 5. Build the drawing XML run ─────────────────────────────────────────
    drawing_run = inline_image_xml(image_rId, cx_emu, cy_emu)

    # Replace the entire <w:r>...<w:t>{{AO-Signature}}</w:t>...</w:r> with drawing run
    # Use a negative-lookahead to prevent the match crossing run boundaries:
    # (?:(?!</w:r>).)* means "any char that is NOT the start of </w:r>"
    AO_RUN_RE = re.compile(
        r'<w:r>(?:(?!</w:r>).)*<w:t[^>]*>\{\{AO-Signature\}\}</w:t>(?:(?!</w:r>).)*</w:r>',
        re.DOTALL
    )
    xml, count = AO_RUN_RE.subn(drawing_run, xml)
    if count == 0:
        # Fallback: plain text replacement (e.g. if rPr is absent)
        xml = xml.replace('{{AO-Signature}}', '')
        print("[WARN] AO-Signature run pattern not matched; placeholder cleared.",
              file=sys.stderr)
    else:
        print(f"[OK] AO signature image inserted ({cx_emu//360000*10/10:.1f} × "
              f"{cy_emu//360000*10/10:.1f} cm)")

    return xml


# ── Spacing fix ──────────────────────────────────────────────────────────────

NEW_SPACING  = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
SPACING_RE   = re.compile(r'<w:spacing\b[^/]*/>')
IND_RE       = re.compile(r'(<w:ind\b[^/]*/>)')
TOP_LEVEL_RE = re.compile(
    r'([ \t]*<w:tbl\b.*?</w:tbl>|[ \t]*<w:p\b.*?</w:p>)',
    re.DOTALL,
)


def has_text(block):
    return bool(re.search(r'<w:t[^/][^>]*>[^<]+', block))


def is_empty_para(block):
    return (block.lstrip().startswith('<w:p')
            and not has_text(block)
            and not re.search(r'<w:br\b', block))


def collapse_empty_paragraph(para):
    """Minimise spacing and add contextualSpacing in schema-correct position."""
    ppr_match = re.search(r'(<w:pPr>)(.*?)(</w:pPr>)', para, re.DOTALL)
    if not ppr_match:
        insert = (f'\n      <w:pPr>\n        {NEW_SPACING}\n'
                  f'        <w:contextualSpacing/>\n      </w:pPr>')
        para = re.sub(r'(<w:p\b[^>]*>)\s*(<w:(?!pPr))',
                      r'\1' + insert + r'\2', para, count=1)
        return para

    ppr_open    = ppr_match.group(1)
    ppr_content = ppr_match.group(2)
    ppr_close   = ppr_match.group(3)

    # Replace or inject <w:spacing> before <w:rPr>
    if SPACING_RE.search(ppr_content):
        ppr_content = SPACING_RE.sub(NEW_SPACING, ppr_content, count=1)
    else:
        if '<w:rPr>' in ppr_content:
            ppr_content = ppr_content.replace(
                '<w:rPr>', NEW_SPACING + '\n        <w:rPr>', 1)
        else:
            ppr_content = '\n        ' + NEW_SPACING + ppr_content

    # Inject <w:contextualSpacing> in schema-correct position
    if '<w:contextualSpacing/>' not in ppr_content:
        if IND_RE.search(ppr_content):
            ppr_content = IND_RE.sub(
                r'\1\n        <w:contextualSpacing/>', ppr_content, count=1)
        elif '<w:jc ' in ppr_content:
            ppr_content = ppr_content.replace(
                '<w:jc ', '<w:contextualSpacing/>\n        <w:jc ', 1)
        elif '<w:rPr>' in ppr_content:
            ppr_content = ppr_content.replace(
                '<w:rPr>', '<w:contextualSpacing/>\n        <w:rPr>', 1)
        else:
            ppr_content += '\n        <w:contextualSpacing/>'

    return para[:ppr_match.start()] + ppr_open + ppr_content + ppr_close + para[ppr_match.end():]


def fix_inter_section_spacing(xml):
    """Collapse spacing on empty inter-table paragraphs to prevent page-top gaps."""
    body_open  = xml.find('<w:body>')
    body_close = xml.rfind('</w:body>')
    if body_open == -1 or body_close == -1:
        return xml

    pre  = xml[:body_open + len('<w:body>')]
    body = xml[body_open + len('<w:body>'): body_close]
    post = xml[body_close:]

    blocks = []
    last = 0
    for m in TOP_LEVEL_RE.finditer(body):
        if m.start() > last:
            blocks.append(('gap', body[last: m.start()]))
        btype = 'tbl' if '<w:tbl' in m.group(1)[:10] else 'para'
        blocks.append((btype, m.group(1)))
        last = m.end()
    if last < len(body):
        blocks.append(('gap', body[last:]))

    last_para_idx = max(
        (i for i, (t, _) in enumerate(blocks) if t == 'para'), default=-1)

    def nearest_content_type(i, direction):
        step = 1 if direction == 'right' else -1
        j = i + step
        while 0 <= j < len(blocks):
            t, c = blocks[j]
            if t == 'gap' or (t == 'para' and is_empty_para(c)):
                j += step
                continue
            return t
        return None

    result = []
    for i, (btype, content) in enumerate(blocks):
        if (btype == 'para'
                and i != last_para_idx
                and is_empty_para(content)):
            left  = nearest_content_type(i, 'left')
            right = nearest_content_type(i, 'right')
            if left == 'tbl' or right == 'tbl':
                content = collapse_empty_paragraph(content)
        result.append(content)

    return pre + ''.join(result) + post


# ── Script helpers ───────────────────────────────────────────────────────────

def locate_scripts():
    for candidate in [
        Path(__file__).parent / "scripts" / "office",
        Path("/mnt/skills/public/docx/scripts/office"),
    ]:
        if (candidate / "unpack.py").exists():
            return candidate
    raise FileNotFoundError("Cannot find unpack.py/pack.py helpers.")


# ── Main ─────────────────────────────────────────────────────────────────────

def process(template_path, data_path, output_path, signature_path=None):
    with open(data_path) as fh:
        content = fh.read()
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml
            raw = yaml.safe_load(content)
        except ImportError:
            raise RuntimeError("pip install pyyaml")

    fields  = raw.get("report_fields", raw)
    mapping = build_mapping(fields)
    scripts = locate_scripts()

    tmp_dir  = os.path.join(tempfile.gettempdir(), "notice_fill_tmp")
    unpacked = os.path.join(tmp_dir, "unpacked")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    subprocess.run([sys.executable, str(scripts / "unpack.py"),
                    template_path, unpacked], check=True)

    doc_path = os.path.join(unpacked, "word", "document.xml")
    with open(doc_path, encoding="utf-8") as fh:
        xml = fh.read()

    xml = fill_borrower_table(xml, fields)        # Step 1
    xml = handle_co_borrowers(xml, fields)         # Step 2
    xml = replace_placeholders(xml, mapping)       # Step 3
    xml = fix_inter_section_spacing(xml)           # Step 4

    # Step 5: AO Signature image (or blank if no image supplied)
    if signature_path and os.path.isfile(signature_path):
        xml = insert_signature_image(xml, unpacked, signature_path)
    else:
        xml = xml.replace('{{AO-Signature}}', '')
        if signature_path:
            print(f"[WARN] Signature file not found: {signature_path}", file=sys.stderr)

    leftovers = sorted(set(re.findall(r"\{\{[^}]+\}\}", xml)))
    if leftovers:
        print(f"[WARN] Unreplaced: {', '.join(leftovers)}", file=sys.stderr)

    with open(doc_path, "w", encoding="utf-8") as fh:
        fh.write(xml)

    subprocess.run([sys.executable, str(scripts / "pack.py"),
                    unpacked, output_path, "--original", template_path],
                   check=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"[OK] Written → {output_path}")


def main():
    p = argparse.ArgumentParser(
        description="Populate a 13(2) SARFAESI notice .docx template.")
    p.add_argument("--template",  required=True, help="Path to template .docx")
    p.add_argument("--data",      required=True, help="Path to report_fields JSON/YAML")
    p.add_argument("--output",    required=True, help="Path for output .docx")
    p.add_argument("--signature", default=None,
                   help="Path to AO signature PNG file (optional)")
    args = p.parse_args()
    process(args.template, args.data, args.output, args.signature)


if __name__ == "__main__":
    main()
