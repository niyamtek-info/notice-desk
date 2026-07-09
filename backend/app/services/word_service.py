import io
import os
import re
import subprocess
import tempfile
from docx import Document
from docx.shared import Inches
from app.core.settings import settings
from app.services.communication_service import (
    build_placeholder_map,
    cleanup_unresolved_brace_placeholders,
    normalize_placeholder_token,
    sanitize_placeholder_value,
)
import time


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
    
    def _replace_placeholders(self, document, data):
        token_pattern = re.compile(r"(\{\{\s*([^{}]+?)\s*\}\}|<\s*([^<>]+?)\s*>)")
        placeholder_map = build_placeholder_map(data)

        def replace_token(match):
            token = match.group(2) or match.group(3) or ""
            normalized = normalize_placeholder_token(token)
            return sanitize_placeholder_value(placeholder_map.get(normalized, ""))

        for paragraph in document.paragraphs:

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

        signature_path = data.get("signature_path")

        if not signature_path:
            return

        if not os.path.exists(signature_path):
            return

        for paragraph in document.paragraphs:

            if re.search(r"<\s*signature_image\s*>", paragraph.text, re.I):
                paragraph.text = re.sub(r"<\s*signature_image\s*>", "", paragraph.text, flags=re.I)

                run = paragraph.add_run()
                run.add_picture(signature_path, width=Inches(1.6))

    # ======================================
    # DOCX → PDF
    # ======================================
    def convert_docx_to_pdf(self, docx_buffer):

        with tempfile.TemporaryDirectory() as tmpdir:

            docx_path = os.path.join(tmpdir, "notice.docx")

            with open(docx_path, "wb") as f:
                f.write(docx_buffer.getvalue())

            subprocess.run([
                settings.LIBREOFFICE_PATH,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmpdir,
                docx_path
            ], check=True)

            pdf_path = os.path.join(tmpdir, "notice.pdf")
            

             # wait for file
            for _ in range(5):
                if os.path.exists(pdf_path):
                    break
                time.sleep(1)

            if not os.path.exists(pdf_path):
                raise Exception("PDF not generated")

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()


        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)

        return buffer
