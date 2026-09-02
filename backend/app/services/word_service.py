import base64
import io
import os
import re
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Inches, Emu, Mm, Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table
from docx.text.paragraph import Paragraph
from app.services.communication_service import (
    build_placeholder_map,
    cleanup_unresolved_brace_placeholders,
    normalize_placeholder_token,
    sanitize_placeholder_value,
)
from app.services.html_docx_renderer import (
    extract_body_default_style,
    extract_table_avoid_break,
    render_html_body,
)


# Default AO signature dimensions (px @ 96 DPI), per spec: Width 105.82px, Height 45.35px
EMU_PER_PIXEL = 9525
AO_SIGNATURE_WIDTH = Emu(round(105.82 * EMU_PER_PIXEL))
AO_SIGNATURE_HEIGHT = Emu(round(45.35 * EMU_PER_PIXEL))

# python-docx's default blank Document has no explicit page size/margins of
# its own - matching pdf_service.py's A4 + margins here keeps the two output
# paths in sync (same content width for wrapping/pagination).
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297
SIDE_MARGIN_MM = 18
TOP_MARGIN_MM = 40
BOTTOM_MARGIN_MM = 30

class WordService:

    # ======================================
    # MAIN GENERATOR
    # ======================================
    def generate_from_template(self, template_path: str, data: dict):

        document = Document(template_path)

        self._replace_placeholders(document, data)
        self._replace_table_placeholders(document, data)
        self._replace_borrower_section(document, data)
        self._insert_signature(document, data)

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        return buffer

    def _iter_all_paragraphs(self, document):
        """Body paragraphs plus every section's header/footer paragraphs.

        python-docx's `document.paragraphs` only covers the body, so
        placeholders (signature/seal/header/footer tokens) living in a
        section's header or footer are silently skipped without this.
        """
        for paragraph in document.paragraphs:
            yield paragraph

        for section in document.sections:
            for part in (
                section.header,
                section.footer,
                section.first_page_header,
                section.first_page_footer,
                section.even_page_header,
                section.even_page_footer,
            ):
                if part is None:
                    continue
                for paragraph in part.paragraphs:
                    yield paragraph
                for table in part.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                yield paragraph

    def _replace_placeholders(self, document, data):
        token_pattern = re.compile(r"(\{\{\s*([^{}]+?)\s*\}\}|<\s*([^<>]+?)\s*>)")
        placeholder_map = build_placeholder_map(data)

        def replace_token(match):
            token = match.group(2) or match.group(3) or ""
            normalized = normalize_placeholder_token(token)
            return sanitize_placeholder_value(placeholder_map.get(normalized, ""))

        for paragraph in self._iter_all_paragraphs(document):

            full_text = "".join(run.text for run in paragraph.runs)
            full_text = token_pattern.sub(replace_token, full_text)
            full_text = cleanup_unresolved_brace_placeholders(full_text)

            if paragraph.runs:
                paragraph.runs[0].text = full_text

                for run in paragraph.runs[1:]:
                    run.text = ""


    # ======================================
    # RUN SAFE PLACEHOLDER REPLACEMENT
    # ======================================
    def _replace_borrower_section(self, document, data):

        borrowers = data.get("borrowers", [])
        property_address = data.get("mortgaged_property_address", "")

        for paragraph in document.paragraphs:

            if re.search(r"<\s*borrower_section\s*>", paragraph.text, re.I):

                parent = paragraph._element.getparent()
                index = parent.index(paragraph._element)

                template_style = paragraph.style
                parent.remove(paragraph._element)

                for idx, borrower in enumerate(borrowers, 1):

                    name = borrower.get("name", "")
                    address = borrower.get("address", "")

                    # borrower name
                    p = document.add_paragraph(style=template_style)
                    run = p.add_run(f"{idx}. {name}")
                    if paragraph.runs:
                        run.font.name = paragraph.runs[0].font.name
                        run.font.size = paragraph.runs[0].font.size
                    run.bold = True

                    parent.insert(index, p._element)
                    index += 1

                    # borrower address
                    if address:
                        for line in address.replace(",", "\n").split("\n"):
                            p = document.add_paragraph(style=template_style)
                            p.add_run(line.strip())

                            parent.insert(index, p._element)
                            index += 1

                    # property address
                    if property_address:
                        p = document.add_paragraph(style=template_style)
                        parent.insert(index, p._element)
                        index += 1

                        for line in property_address.split("\n"):
                            p = document.add_paragraph(style=template_style)
                            p.add_run(line.strip())

                            parent.insert(index, p._element)
                            index += 1

                    # spacing
                    p = document.add_paragraph(style=template_style)
                    parent.insert(index, p._element)
                    index += 1

    # ======================================
    # TABLE PLACEHOLDER REPLACEMENT
    # ======================================
    def _replace_table_placeholders(self, document, data):
        token_pattern = re.compile(r"(\{\{\s*([^{}]+?)\s*\}\}|<\s*([^<>]+?)\s*>)")
        placeholder_map = build_placeholder_map(data)

        def replace_token(match):
            token = match.group(2) or match.group(3) or ""
            normalized = normalize_placeholder_token(token)
            return sanitize_placeholder_value(placeholder_map.get(normalized, ""))

        for table in document.tables:

            for row in table.rows:

                for cell in row.cells:

                    for paragraph in cell.paragraphs:

                        full_text = "".join(run.text for run in paragraph.runs)
                        full_text = token_pattern.sub(replace_token, full_text)
                        full_text = cleanup_unresolved_brace_placeholders(full_text)

                        if paragraph.runs:
                            paragraph.runs[0].text = full_text
                            for run in paragraph.runs[1:]:
                                run.text = ""

    # ======================================
    # SIGNATURE INSERT
    # ======================================
    def _insert_signature(self, document, data):

        signature_path = data.get("signature_path") or data.get("ao_signature_path")

        if not signature_path:
            return

        if not os.path.exists(signature_path):
            return

        for paragraph in self._iter_all_paragraphs(document):

            if re.search(r"<\s*signature_image\s*>", paragraph.text, re.I):
                paragraph.text = re.sub(r"<\s*signature_image\s*>", "", paragraph.text, flags=re.I)

                run = paragraph.add_run()
                run.add_picture(signature_path, width=AO_SIGNATURE_WIDTH, height=AO_SIGNATURE_HEIGHT)

    # ======================================
    # HTML → DOCX (direct render, no Pandoc)
    # ======================================
    def generate_docx_from_html(self, html: str) -> io.BytesIO:

        html = re.sub(r"<title>.*?</title>", "", html, flags=re.IGNORECASE | re.DOTALL)

        # Real <header>/<footer> tags (letterhead logo, trustee seal) need to
        # repeat on every page. Word has native per-section header/footer
        # support for that, so pull them out of the flowed body content and
        # re-apply them afterwards as section header/footer.
        soup = BeautifulSoup(html, "html.parser")
        header_tag = soup.find("header")
        footer_tag = soup.find("footer")
        header_images = self._extract_band_images(header_tag)
        header_alignment = self._extract_band_alignment(header_tag)
        footer_images = self._extract_band_images(footer_tag)
        footer_alignment = self._extract_band_alignment(footer_tag)
        if header_tag is not None:
            header_tag.extract()
        if footer_tag is not None:
            footer_tag.extract()

        document = Document()
        # Any element with no font of its own falls back to whatever the
        # template's own `body { font-family; font-size }` rule says in a
        # browser - a blank python-docx Document instead falls back to its
        # built-in Calibri/11pt theme default. Read the template's own rule
        # (if it declares one) rather than assuming a fixed font, so this
        # still works correctly for a template with a different default.
        default_family, default_size_pt = extract_body_default_style(soup)
        if default_family or default_size_pt:
            normal_style = document.styles["Normal"]
            if default_family:
                normal_style.font.name = default_family
            if default_size_pt:
                normal_style.font.size = Pt(default_size_pt)

        # Margins are fixed to match pdf_service (SIDE_MARGIN_MM etc.) - the
        # PDF path deliberately overrides the template's own `@page` rule with
        # those same constants, so the .docx has to use them too or the two
        # outputs disagree on where the content box sits.
        content_width_twips = self._set_page_size(document)
        max_band_width_emu = Emu(round(content_width_twips * 635))

        avoid_row_split = extract_table_avoid_break(soup)
        body_tag = soup.find("body") or soup
        render_html_body(document, body_tag, content_width_twips, max_band_width_emu, avoid_row_split)

        self._prevent_signature_block_split(document)

        # Header/footer bands are authored as full-bleed letterhead art (the
        # header banner is 809x119px ~= 214mm wide - wider than the A4 page
        # itself) meant to touch both page edges, unlike body content which
        # is confined to the margins. Clamp against the full page width, not
        # the margin-narrowed content width, and cancel the side margins on
        # the band paragraph itself so the image can actually reach x=0.
        full_page_width_emu = Emu(Mm(PAGE_WIDTH_MM))
        side_margin_emu = Emu(Mm(SIDE_MARGIN_MM))

        for section in document.sections:
            section.header_distance = Mm(0)
            section.footer_distance = Mm(0)
            self._apply_band_content(
                section.header, header_images, header_alignment, full_page_width_emu, side_margin_emu
            )
            self._apply_band_content(
                section.footer, footer_images, footer_alignment, full_page_width_emu, side_margin_emu
            )

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        return buffer

    def _extract_band_images(self, tag) -> list[tuple[bytes, "Emu | None", "Emu | None"]]:
        images = []
        if tag is None:
            return images

        for img in tag.find_all("img"):
            src = img.get("src", "")
            match = re.match(r"data:image/[^;]+;base64,(.+)", src, re.DOTALL)
            if not match:
                continue
            try:
                image_bytes = base64.b64decode(match.group(1))
            except Exception:
                continue

            style = img.get("style", "") or ""
            width_match = re.search(r"width\s*:\s*([\d.]+)px", style, re.I)
            height_match = re.search(r"height\s*:\s*([\d.]+)px", style, re.I)
            width = Emu(round(float(width_match.group(1)) * EMU_PER_PIXEL)) if width_match else None
            height = Emu(round(float(height_match.group(1)) * EMU_PER_PIXEL)) if height_match else None
            images.append((image_bytes, width, height))

        return images

    def _extract_band_alignment(self, tag):
        if tag is None:
            return None
        first_p = tag.find("p")
        if first_p is None:
            return None
        style = first_p.get("style", "") or ""
        match = re.search(r"text-align\s*:\s*(left|center|right)", style, re.I)
        if not match:
            return None
        return {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }[match.group(1).lower()]

    def _apply_band_content(self, band, images, alignment, max_width_emu=None, side_margin_emu=None) -> None:
        if not images:
            return

        band.is_linked_to_previous = False
        paragraph = band.paragraphs[0] if band.paragraphs else band.add_paragraph()
        if alignment is not None:
            paragraph.alignment = alignment
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        if side_margin_emu is not None:
            # Widen the paragraph's drawable area from the margin-narrowed
            # content box back out to the full page width so a full-bleed
            # band image can start at x=0 instead of x=left_margin.
            paragraph.paragraph_format.left_indent = Emu(-side_margin_emu)
            paragraph.paragraph_format.right_indent = Emu(-side_margin_emu)

        for image_bytes, width, height in images:
            # The source HTML sizes these against a browser's print viewport,
            # which auto-shrinks via CSS max-width to fit the page. Word does
            # not - an oversized inline picture just overflows past the page
            # edge - so clamp it to the section's actual usable width here.
            if width and height and max_width_emu and width > max_width_emu:
                height = Emu(round(height * (max_width_emu / width)))
                width = Emu(max_width_emu)

            run = paragraph.add_run()
            if width and height:
                run.add_picture(io.BytesIO(image_bytes), width=width, height=height)
            else:
                run.add_picture(io.BytesIO(image_bytes))

    def _prevent_signature_block_split(self, document) -> None:
        # The AO signature image sits in one table, and the "FOR ... Limited /
        # (Name) / Authorised Officer" text sits in the very next table.
        # Word treats each paragraph as an independent break point by
        # default, so a page boundary can land in the middle of that group -
        # e.g. leaving "(Name)" and "Authorised Officer" alone at the top of
        # a new page while the image and heading stay behind. keep_with_next
        # glues each paragraph to the one after it so the whole group moves
        # together.
        body = document.element.body
        children = list(body)

        for idx, child in enumerate(children):
            if child.tag != qn("w:tbl"):
                continue

            table = Table(child, document)
            paragraphs = [p for row in table.rows for cell in row.cells for p in cell.paragraphs]
            if not paragraphs:
                continue

            # Match the signature block specifically (a short standalone
            # "Authorised/Authorized Officer" line), not clauses that merely
            # mention the term in running legal text (e.g. "...addressed to
            # the Authorized Officer at authorised.officer@...").
            last_text = paragraphs[-1].text.strip().lower()
            if last_text not in ("authorised officer", "authorized officer"):
                continue
            for paragraph in paragraphs[:-1]:
                paragraph.paragraph_format.keep_with_next = True

            # Walk backwards over any stray empty paragraphs between tables,
            # gluing each to the next, until the actual signature-image
            # table (or other real content) is reached - so the whole chain
            # moves together instead of just the last link.
            back = idx - 1
            while back >= 0:
                previous = children[back]
                if previous.tag == qn("w:tbl"):
                    previous_table = Table(previous, document)
                    for row in previous_table.rows:
                        for cell in row.cells:
                            # Every paragraph in this table, not just the
                            # last one per cell - e.g. the signature image
                            # itself sits in a middle paragraph, and only
                            # chaining the final (often empty) paragraph
                            # left the image free to be separated from the
                            # text that must follow it.
                            for paragraph in cell.paragraphs:
                                paragraph.paragraph_format.keep_with_next = True
                    break
                if previous.tag == qn("w:p"):
                    previous_paragraph = Paragraph(previous, document)
                    previous_paragraph.paragraph_format.keep_with_next = True
                    if previous_paragraph.text.strip():
                        break
                    back -= 1
                    continue
                break

    def _set_page_size(self, document) -> int:
        """Returns the resulting content width in twips (page width minus
        left/right margins), so callers can rescale table widths to match."""
        for section in document.sections:
            section.page_width = Mm(PAGE_WIDTH_MM)
            section.page_height = Mm(PAGE_HEIGHT_MM)
            section.left_margin = Mm(SIDE_MARGIN_MM)
            section.right_margin = Mm(SIDE_MARGIN_MM)
            section.top_margin = Mm(TOP_MARGIN_MM)
            section.bottom_margin = Mm(BOTTOM_MARGIN_MM)

        content_width = Mm(PAGE_WIDTH_MM - 2 * SIDE_MARGIN_MM)
        return content_width.twips

