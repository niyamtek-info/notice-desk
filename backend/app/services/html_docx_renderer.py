import base64
import io
import re
from dataclasses import dataclass

from bs4 import NavigableString, Tag
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor, Twips

# Renders the notice body HTML directly into a python-docx Document, reading
# each element's own inline style (table <col> widths, cell border-style,
# span font-size/font-family/color) instead of handing the HTML to Pandoc
# and then guessing what it threw away from a handful of known table shapes.
# That guessing (regex-matching "1." / "a)" marker cells, "(Borrower)" role
# tags, "Loan Account" table text) only ever covered the one template it was
# built against - any template authored with a different table/paragraph
# structure would fall through every heuristic. Reading the style attributes
# directly instead means formatting survives verbatim for any template; only
# placeholder text differs between notices.

EMU_PER_PIXEL = 9525

_ALIGN_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*pt", re.I)
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.I)
_COLOR_RE = re.compile(r"(?<!background-)(?<!-)color\s*:\s*([^;]+)", re.I)
_WIDTH_PX_RE = re.compile(r"width\s*:\s*([\d.]+)\s*px", re.I)
_HEIGHT_PX_RE = re.compile(r"height\s*:\s*([\d.]+)\s*px", re.I)
_TEXT_ALIGN_RE = re.compile(r"text-align\s*:\s*(left|right|center|justify)", re.I)
_BORDER_STYLE_RE = re.compile(r"border-style\s*:\s*(\w+)", re.I)
_BORDER_WIDTH_PX_RE = re.compile(r"border-width\s*:\s*([\d.]+)\s*px", re.I)

_NAMED_COLORS = {
    "black": "000000",
    "windowtext": "000000",
    "currentcolor": "000000",
    "white": "FFFFFF",
}

_BODY_RULE_RE = re.compile(r"(?:^|\})\s*body\s*\{([^}]*)\}", re.I)
_TABLE_RULE_RE = re.compile(r"(?:^|\})\s*table\s*\{([^}]*)\}", re.I)
_PAGE_BREAK_AVOID_RE = re.compile(r"page-break-inside\s*:\s*avoid", re.I)


def extract_table_avoid_break(soup) -> bool:
    """True if the template's own stylesheet declares
    `table { page-break-inside: avoid }` (checked anywhere in the whole
    <style> block, since the rule may sit inside an `@media print` block
    rather than the bare `table` selector) - read from the template rather
    than assumed, since a different template may not want this at all."""
    style_tag = soup.find("style")
    if style_tag is None:
        return False
    css_text = style_tag.get_text()
    match = _TABLE_RULE_RE.search(css_text)
    if match and _PAGE_BREAK_AVOID_RE.search(match.group(1)):
        return True
    return bool(_PAGE_BREAK_AVOID_RE.search(css_text))


def extract_body_default_style(soup) -> "tuple[str | None, float | None]":
    """Reads the template's own `body { font-family: ...; font-size: ... }`
    rule from its <style> block, if any. This is the cascade root a browser
    falls back to for any element with no font of its own - reading it
    keeps that fallback template-driven instead of guessing a fixed font
    that would only be right for the one template it was picked from."""
    style_tag = soup.find("style")
    if style_tag is None:
        return None, None

    match = _BODY_RULE_RE.search(style_tag.get_text())
    if not match:
        return None, None

    declaration = match.group(1)

    family = None
    family_match = _FONT_FAMILY_RE.search(declaration)
    if family_match:
        family = family_match.group(1).split(",")[0].strip().strip('"').strip("'")

    size_pt = None
    size_match = _FONT_SIZE_RE.search(declaration)
    if size_match:
        size_pt = float(size_match.group(1))

    return family, size_pt


@dataclass(frozen=True)
class _RunStyle:
    size_pt: float | None = None
    family: str | None = None
    color: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False


def _parse_color(value: str) -> str | None:
    value = value.strip().strip('"').strip("'").lower()
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]
    if value.startswith("#"):
        hex_part = value[1:]
        if len(hex_part) == 3:
            hex_part = "".join(ch * 2 for ch in hex_part)
        if len(hex_part) == 6 and all(c in "0123456789abcdef" for c in hex_part):
            return hex_part.upper()
        return None
    match = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", value)
    if match:
        return "".join(f"{int(c):02X}" for c in match.groups())
    return None


def _merge_style_from_tag(tag: Tag, style: _RunStyle) -> _RunStyle:
    css = tag.get("style", "") or ""

    size_pt = style.size_pt
    match = _FONT_SIZE_RE.search(css)
    if match:
        size_pt = float(match.group(1))

    family = style.family
    match = _FONT_FAMILY_RE.search(css)
    if match:
        family = match.group(1).split(",")[0].strip().strip('"').strip("'")

    color = style.color
    match = _COLOR_RE.search(css)
    if match:
        parsed = _parse_color(match.group(1))
        if parsed:
            color = parsed

    name = (tag.name or "").lower()
    bold = style.bold or name in ("strong", "b")
    italic = style.italic or name in ("em", "i")
    underline = style.underline or name == "u"

    return _RunStyle(size_pt=size_pt, family=family, color=color, bold=bold, italic=italic, underline=underline)


def _apply_run_style(run, style: _RunStyle) -> None:
    if style.size_pt is not None:
        run.font.size = Pt(style.size_pt)
    if style.family:
        run.font.name = style.family
    if style.color:
        run.font.color.rgb = RGBColor.from_string(style.color)
    if style.bold:
        run.font.bold = True
    if style.italic:
        run.font.italic = True
    if style.underline:
        run.font.underline = True


def _render_image(paragraph, img_tag: Tag, max_width_emu: "Emu | None") -> None:
    src = img_tag.get("src", "")
    match = re.match(r"data:image/[^;]+;base64,(.+)", src, re.DOTALL)
    if not match:
        return
    try:
        image_bytes = base64.b64decode(match.group(1))
    except Exception:
        return

    css = img_tag.get("style", "") or ""
    width_match = _WIDTH_PX_RE.search(css)
    height_match = _HEIGHT_PX_RE.search(css)
    # "height:auto" (or no height at all) is common alongside an explicit
    # width - python-docx's add_picture already preserves aspect ratio when
    # only one dimension is passed, same as CSS "auto" would, so treat width
    # and height as independently optional rather than requiring both.
    width = Emu(round(float(width_match.group(1)) * EMU_PER_PIXEL)) if width_match else None
    height = Emu(round(float(height_match.group(1)) * EMU_PER_PIXEL)) if height_match else None

    if width and max_width_emu and width > max_width_emu:
        if height:
            height = Emu(round(height * (max_width_emu / width)))
        width = Emu(max_width_emu)

    run = paragraph.add_run()
    kwargs = {}
    if width:
        kwargs["width"] = width
    if height:
        kwargs["height"] = height
    run.add_picture(io.BytesIO(image_bytes), **kwargs)


def _render_inline(paragraph, node, style: _RunStyle, max_width_emu: "Emu | None") -> None:
    if isinstance(node, NavigableString):
        text = str(node)
        if not text:
            return
        run = paragraph.add_run(text)
        _apply_run_style(run, style)
        return

    if not isinstance(node, Tag):
        return

    name = node.name.lower()

    if name == "br":
        paragraph.add_run().add_break()
        return

    if name == "img":
        _render_image(paragraph, node, max_width_emu)
        return

    child_style = _merge_style_from_tag(node, style)
    for child in node.children:
        _render_inline(paragraph, child, child_style, max_width_emu)


def _render_paragraph(container, p_tag: Tag, max_width_emu: "Emu | None" = None):
    paragraph = container.add_paragraph()

    align_match = _TEXT_ALIGN_RE.search(p_tag.get("style", "") or "")
    if align_match:
        paragraph.alignment = _ALIGN_MAP.get(align_match.group(1).lower())

    for child in p_tag.children:
        _render_inline(paragraph, child, _RunStyle(), max_width_emu)

    return paragraph


def _col_widths_twips(table_tag: Tag, content_width_twips: int) -> "list[int] | None":
    colgroup = table_tag.find("colgroup")
    if colgroup is None:
        return None
    cols = colgroup.find_all("col")
    if not cols:
        return None

    px_widths = []
    for col in cols:
        match = _WIDTH_PX_RE.search(col.get("style", "") or "")
        if not match:
            return None
        px_widths.append(float(match.group(1)))

    total_px = sum(px_widths)
    if total_px <= 0:
        return None

    return [round(px / total_px * content_width_twips) for px in px_widths]


def _cell_border_size_eighths_pt(cell_tag: Tag) -> "int | None":
    style = cell_tag.get("style", "") or ""
    match = _BORDER_STYLE_RE.search(style)
    if not match or match.group(1).lower() != "solid":
        return None

    width_match = _BORDER_WIDTH_PX_RE.search(style)
    px = float(width_match.group(1)) if width_match else 1.0
    return max(round(px * 0.75 * 8), 2)


def _set_cell_borders(cell, size_eighths_pt: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        edge_el = OxmlElement(f"w:{edge}")
        edge_el.set(qn("w:val"), "single")
        edge_el.set(qn("w:sz"), str(size_eighths_pt))
        edge_el.set(qn("w:space"), "0")
        edge_el.set(qn("w:color"), "000000")
        borders.append(edge_el)
    tc_pr.append(borders)


def _render_table(
    document, table_tag: Tag, content_width_twips: int, max_width_emu: "Emu | None", avoid_row_split: bool = False
):
    rows = table_tag.find_all("tr", recursive=True)
    if not rows:
        return None

    num_cols = len(rows[0].find_all(["td", "th"], recursive=False))
    if num_cols == 0:
        return None

    table = document.add_table(rows=len(rows), cols=num_cols)
    table.autofit = False

    widths = _col_widths_twips(table_tag, content_width_twips)
    if not widths or len(widths) != num_cols:
        widths = [content_width_twips // num_cols] * num_cols

    # A table with at least one visibly-bordered cell is real content (e.g.
    # a summary table), as opposed to the borderless tables used purely for
    # layout/alignment - only the former should be kept off a page break,
    # same signal already used above to decide whether to draw cell borders
    # at all. `avoid_row_split` remains a template-wide opt-in on top of this.
    table_is_visible = any(
        _cell_border_size_eighths_pt(cell_tag) is not None
        for tr in rows
        for cell_tag in tr.find_all(["td", "th"], recursive=False)
    )
    avoid_row_split = avoid_row_split or table_is_visible

    for row_idx, tr in enumerate(rows):
        if avoid_row_split:
            # OOXML has no whole-table "keep together" flag; w:cantSplit per
            # row is the equivalent that matters in practice - it stops a
            # row's own content splitting mid-way across a page boundary.
            row_tr_pr = table.rows[row_idx]._tr.get_or_add_trPr()
            row_tr_pr.append(OxmlElement("w:cantSplit"))

        cell_tags = tr.find_all(["td", "th"], recursive=False)
        for col_idx, cell_tag in enumerate(cell_tags):
            if col_idx >= num_cols:
                break
            cell = table.rows[row_idx].cells[col_idx]
            cell.width = Twips(widths[col_idx])

            # drop the blank paragraph python-docx seeds every new cell with
            default_p = cell.paragraphs[0]._element
            default_p.getparent().remove(default_p)

            p_tags = cell_tag.find_all("p", recursive=False)
            if p_tags:
                for p_tag in p_tags:
                    _render_paragraph(cell, p_tag, max_width_emu)
            else:
                _render_paragraph(cell, cell_tag, max_width_emu)

            border_size = _cell_border_size_eighths_pt(cell_tag)
            if border_size is not None:
                _set_cell_borders(cell, border_size)

        if avoid_row_split and row_idx < len(rows) - 1:
            # cantSplit above only stops a single row from breaking
            # mid-content - a page break can still land cleanly *between*
            # two rows, which is exactly what page-break-inside: avoid also
            # forbids for the table as a whole. OOXML has no whole-table
            # "keep together" flag either, so chain every row to the next
            # one via keep_with_next the same way, up to the last row.
            for cell in table.rows[row_idx].cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True

    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for grid_col, width in zip(grid.findall(qn("w:gridCol")), widths):
            grid_col.set(qn("w:w"), str(width))

    return table


def render_html_body(
    document, body_tag: Tag, content_width_twips: int, max_width_emu: "Emu | None" = None, avoid_row_split: bool = False
) -> None:
    """Renders every top-level <p>/<table> under `body_tag` directly onto
    `document`, in order. Call after header/footer <tag>s have already been
    extracted from `body_tag` by the caller."""
    for child in body_tag.find_all(["p", "table"], recursive=False):
        if child.name == "table":
            _render_table(document, child, content_width_twips, max_width_emu, avoid_row_split)
        else:
            _render_paragraph(document, child, max_width_emu)
