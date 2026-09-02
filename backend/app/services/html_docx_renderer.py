import base64
import io
import re
from dataclasses import dataclass

from bs4 import NavigableString, Tag
from docx.enum.table import WD_ALIGN_VERTICAL
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
_VERTICAL_ALIGN_RE = re.compile(r"vertical-align\s*:\s*(top|middle|bottom)", re.I)
_BORDER_STYLE_RE = re.compile(r"border-style\s*:\s*(\w+)", re.I)
_BORDER_WIDTH_PX_RE = re.compile(r"border-width\s*:\s*([\d.]+)\s*px", re.I)

# A <col> `width:` in any unit - the numeric part is used only as a relative
# weight (renormalised against the row total), so px, pt and % can be mixed
# here without converting between them.
_WIDTH_WEIGHT_RE = re.compile(r"(?<!-)width\s*:\s*([\d.]+)\s*(?:px|pt|%)", re.I)

_HEADING_SIZES_PT = {"h1": 20.0, "h2": 16.0, "h3": 13.0, "h4": 12.0, "h5": 11.0, "h6": 10.0}
# Wrappers that carry no block semantics of their own - descend through them
# so content nested in a layout <div> is rendered instead of skipped.
_TRANSPARENT_CONTAINERS = {"div", "section", "article", "main"}

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


def _render_paragraph(container, p_tag: Tag, max_width_emu: "Emu | None" = None, default_align=None):
    paragraph = container.add_paragraph()

    align_match = _TEXT_ALIGN_RE.search(p_tag.get("style", "") or "")
    if align_match:
        paragraph.alignment = _ALIGN_MAP.get(align_match.group(1).lower())
    elif default_align is not None:
        # The <p> declares no alignment of its own - inherit the enclosing
        # cell's `text-align` (CSS would; python-docx will not without this).
        paragraph.alignment = default_align

    for child in p_tag.children:
        _render_inline(paragraph, child, _RunStyle(), max_width_emu)

    return paragraph


def _own_align(tag: Tag):
    """The `text-align` declared on this element itself, mapped to a docx
    alignment - or None when it declares none."""
    if not isinstance(tag, Tag):
        return None
    match = _TEXT_ALIGN_RE.search(tag.get("style", "") or "")
    return _ALIGN_MAP.get(match.group(1).lower()) if match else None


def _render_heading(container, tag: Tag, max_width_emu: "Emu | None" = None, default_align=None):
    paragraph = _render_paragraph(container, tag, max_width_emu, default_align=default_align)
    size_pt = _HEADING_SIZES_PT.get(tag.name.lower())
    for run in paragraph.runs:
        run.font.bold = True
        if size_pt is not None and run.font.size is None:
            run.font.size = Pt(size_pt)
    return paragraph


def _render_list(container, list_tag: Tag, max_width_emu: "Emu | None", ordered: bool, default_align=None):
    for idx, li in enumerate(list_tag.find_all("li", recursive=False), 1):
        paragraph = container.add_paragraph()
        if _own_align(li) is not None:
            paragraph.alignment = _own_align(li)
        elif default_align is not None:
            paragraph.alignment = default_align
        paragraph.add_run(f"{idx}. " if ordered else "• ")
        for child in li.children:
            # A nested <ul>/<ol> is flattened inline here; deep nesting is not
            # something the notice templates use.
            _render_inline(paragraph, child, _RunStyle(), max_width_emu)
        paragraph.paragraph_format.left_indent = Pt(18)


def _col_widths_twips(table_tag: Tag, total_twips: int) -> "list[int] | None":
    colgroup = table_tag.find("colgroup")
    if colgroup is None:
        return None
    cols = colgroup.find_all("col")
    if not cols:
        return None

    weights = []
    for col in cols:
        match = _WIDTH_WEIGHT_RE.search(col.get("style", "") or "")
        if not match:
            return None
        weights.append(float(match.group(1)))

    total = sum(weights)
    if total <= 0:
        return None

    return [round(w / total * total_twips) for w in weights]


def _int_attr(tag: Tag, name: str) -> int:
    """A `colspan`/`rowspan` attribute as an int >= 1, tolerant of missing,
    empty, or malformed values."""
    try:
        return max(1, int(tag.get(name) or 1))
    except (TypeError, ValueError):
        return 1


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
    document,
    table_tag: Tag,
    content_width_twips: int,
    max_width_emu: "Emu | None",
    avoid_row_split: bool = False,
    inherited_align=None,
):
    rows = table_tag.find_all("tr", recursive=True)
    if not rows:
        return None

    # `text-align` in effect for this table's cells, unless a cell/paragraph
    # overrides it - the table's own declaration, else whatever was inherited
    # from an ancestor (CSS `text-align` inherits; python-docx does not).
    table_align = _own_align(table_tag) or inherited_align

    # True grid column count. The <colgroup> is authoritative when present;
    # otherwise take the widest row once every cell's colspan is counted (a
    # plain `len(first row cells)` under-counts any row that uses colspan).
    colgroup = table_tag.find("colgroup")
    col_tags = colgroup.find_all("col") if colgroup is not None else []
    if col_tags:
        num_cols = len(col_tags)
    else:
        num_cols = max(
            (
                sum(_int_attr(c, "colspan") for c in tr.find_all(["td", "th"], recursive=False))
                for tr in rows
            ),
            default=0,
        )
    if num_cols == 0:
        return None

    table = document.add_table(rows=len(rows), cols=num_cols)
    table.autofit = False

    # Every table fills the full content width. This matches the PDF path,
    # which forces `table { width: 100% !important }` in _inject_print_styles
    # and ignores any authored `style="width: NNNpx"` - the .docx must do the
    # same or the two outputs place tables differently.
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

    # Grid coordinates already consumed by a colspan/rowspan reaching in from
    # an earlier cell - the next cell tag in a row skips over these.
    occupied: "set[tuple[int, int]]" = set()

    for row_idx, tr in enumerate(rows):
        if avoid_row_split:
            # OOXML has no whole-table "keep together" flag; w:cantSplit per
            # row is the equivalent that matters in practice - it stops a
            # row's own content splitting mid-way across a page boundary.
            row_tr_pr = table.rows[row_idx]._tr.get_or_add_trPr()
            row_tr_pr.append(OxmlElement("w:cantSplit"))

        grid_col = 0
        for cell_tag in tr.find_all(["td", "th"], recursive=False):
            while (row_idx, grid_col) in occupied:
                grid_col += 1
            if grid_col >= num_cols:
                break

            colspan = min(_int_attr(cell_tag, "colspan"), num_cols - grid_col)
            rowspan = min(_int_attr(cell_tag, "rowspan"), len(rows) - row_idx)

            cell = table.cell(row_idx, grid_col)
            if colspan > 1 or rowspan > 1:
                cell = cell.merge(table.cell(row_idx + rowspan - 1, grid_col + colspan - 1))
            for rr in range(row_idx, row_idx + rowspan):
                for cc in range(grid_col, grid_col + colspan):
                    occupied.add((rr, cc))

            cell.width = Twips(sum(widths[grid_col:grid_col + colspan]))

            cell_style = cell_tag.get("style", "") or ""
            align_match = _TEXT_ALIGN_RE.search(cell_style)
            cell_align = _ALIGN_MAP.get(align_match.group(1).lower()) if align_match else table_align
            valign_match = _VERTICAL_ALIGN_RE.search(cell_style)
            if valign_match:
                cell.vertical_alignment = {
                    "top": WD_ALIGN_VERTICAL.TOP,
                    "middle": WD_ALIGN_VERTICAL.CENTER,
                    "bottom": WD_ALIGN_VERTICAL.BOTTOM,
                }[valign_match.group(1).lower()]

            # Clear the paragraphs the cell arrived with - a fresh cell has one
            # blank, a just-merged cell has one per grid column it now spans -
            # then render the real content into it.
            for para in list(cell.paragraphs):
                para._element.getparent().remove(para._element)

            p_tags = cell_tag.find_all("p", recursive=False)
            if p_tags:
                for p_tag in p_tags:
                    _render_paragraph(cell, p_tag, max_width_emu, default_align=cell_align)
            else:
                _render_paragraph(cell, cell_tag, max_width_emu, default_align=cell_align)

            if not cell.paragraphs:
                # OOXML requires every cell to hold at least one paragraph.
                cell.add_paragraph()

            border_size = _cell_border_size_eighths_pt(cell_tag)
            if border_size is not None:
                _set_cell_borders(cell, border_size)

            grid_col += colspan

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
        for grid_col_el, width in zip(grid.findall(qn("w:gridCol")), widths):
            grid_col_el.set(qn("w:w"), str(width))

    return table


def render_html_body(
    document,
    body_tag: Tag,
    content_width_twips: int,
    max_width_emu: "Emu | None" = None,
    avoid_row_split: bool = False,
    inherited_align=None,
) -> None:
    """Renders the block-level content under `body_tag` directly onto
    `document`, in document order. Layout-only wrappers (`<div>` etc.) are
    transparent - their children are rendered as if they sat at body level -
    and headings/lists are rendered too, so a template change that adds any
    of these is reflected in the .docx instead of silently dropped.

    `inherited_align` carries a `text-align` down from an ancestor element
    (CSS inherits it; python-docx does not), so e.g. a
    `<div style="text-align:center">` wrapping the closing contact block
    centres those paragraphs in the .docx the way it does in the PDF. Call
    after header/footer <tag>s have already been extracted by the caller."""
    for child in body_tag.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                paragraph = document.add_paragraph()
                if inherited_align is not None:
                    paragraph.alignment = inherited_align
                paragraph.add_run(text)
            continue
        if not isinstance(child, Tag):
            continue

        name = (child.name or "").lower()
        applied_align = _own_align(child) or inherited_align
        if name == "table":
            _render_table(
                document, child, content_width_twips, max_width_emu, avoid_row_split, inherited_align
            )
        elif name in _HEADING_SIZES_PT:
            _render_heading(document, child, max_width_emu, default_align=applied_align)
        elif name in ("ul", "ol"):
            _render_list(document, child, max_width_emu, ordered=(name == "ol"), default_align=applied_align)
        elif name == "blockquote":
            for p_tag in child.find_all("p", recursive=False) or [child]:
                quoted = _render_paragraph(document, p_tag, max_width_emu, default_align=applied_align)
                quoted.paragraph_format.left_indent = Pt(24)
        elif name == "hr":
            document.add_paragraph()
        elif name in _TRANSPARENT_CONTAINERS:
            render_html_body(document, child, content_width_twips, max_width_emu, avoid_row_split, applied_align)
        elif name == "p":
            _render_paragraph(document, child, max_width_emu, default_align=applied_align)
        # Any other bare inline tag at block level (e.g. a stray <strong>) is
        # not a block container - fall through and ignore it.
