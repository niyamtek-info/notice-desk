import base64
import html
import io
import re
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import urllib.request
from pathlib import Path
from typing import Any
import asyncio

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass

from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Image,
    Frame,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.settings import settings

# ─────────────────────────────────────────────────────────────────────────────
# fonts.yaml registry
# ─────────────────────────────────────────────────────────────────────────────
_FONTS_YAML_PATH = Path(__file__).parent.parent / "storage" / "fonts" / "fonts.yaml"
_FONTS_REGISTRY_CACHE: list[dict] | None = None   # flat list of font dicts


def _load_fonts_registry() -> list[dict]:
    """Parse fonts.yaml once and return a flat list of font records."""
    global _FONTS_REGISTRY_CACHE
    if _FONTS_REGISTRY_CACHE is not None:
        return _FONTS_REGISTRY_CACHE

    if not _YAML_AVAILABLE or not _FONTS_YAML_PATH.exists():
        _FONTS_REGISTRY_CACHE = []
        return _FONTS_REGISTRY_CACHE

    try:
        with open(_FONTS_YAML_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        records: list[dict] = []
        for category_block in data.get("fonts", []):
            for font in category_block.get("fonts", []):
                records.append(font)
        _FONTS_REGISTRY_CACHE = records
        print(f"[FONT_REGISTRY] Loaded {len(records)} fonts from fonts.yaml")
    except Exception as exc:
        print(f"[FONT_REGISTRY] Failed to load fonts.yaml: {exc}")
        _FONTS_REGISTRY_CACHE = []

    return _FONTS_REGISTRY_CACHE


def _normalize_name(name: str) -> str:
    """Lowercase, strip spaces and punctuation for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _find_font_in_registry(family_name: str) -> dict | None:
    """Return the registry entry whose name matches family_name (fuzzy)."""
    key = _normalize_name(family_name)
    for record in _load_fonts_registry():
        if _normalize_name(record.get("name", "")) == key:
            return record
    return None


def _google_font_cache_path(family_name: str) -> Path:
    """Path where a downloaded Google Font .ttf is cached."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", family_name)
    return _FONTS_YAML_PATH.parent / f"gf_{safe}.ttf"


def _download_google_font_ttf(family_name: str, import_url: str) -> Path | None:
    """
    Download a TTF for *family_name* from the Google Fonts CSS2 API.
    Returns the cached Path or None on failure.
    """
    cache_path = _google_font_cache_path(family_name)
    if cache_path.exists():
        return cache_path

    try:
        # Ask Google Fonts for the CSS; use a desktop UA so we get TTF/WOFF2.
        css_url = import_url.rstrip("&") + "&display=swap"
        req = urllib.request.Request(
            css_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            css_text = resp.read().decode("utf-8", errors="replace")

        # Extract first src URL from the CSS response
        match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.(?:ttf|woff2?))\)", css_text)
        if not match:
            print(f"[FONT_REGISTRY] No font URL found in Google Fonts CSS for '{family_name}'")
            return None

        font_url = match.group(1)
        font_req = urllib.request.Request(font_url, headers={"Referer": "https://fonts.googleapis.com/"})
        with urllib.request.urlopen(font_req, timeout=15) as resp:
            font_bytes = resp.read()

        cache_path.write_bytes(font_bytes)
        print(f"[FONT_REGISTRY] Downloaded and cached '{family_name}' → {cache_path.name}")
        return cache_path

    except Exception as exc:
        print(f"[FONT_REGISTRY] Download failed for '{family_name}': {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Layout constants
# ─────────────────────────────────────────────────────────────────────────────
HEADER_HEIGHT_MM = 36
FOOTER_HEIGHT_MM = 30
SIDE_MARGIN_MM   = 18

# Chromium injects ~5px top bleed into header/footer templates.
# We compensate in the template CSS by shifting content up.
_CHROMIUM_HEADER_BLEED_MM = 5

# Default AO signature dimensions (px @ 96 DPI -> reportlab points, 1px = 0.75pt)
AO_SIGNATURE_WIDTH_PT = 105.82 * 0.75
AO_SIGNATURE_HEIGHT_PT = 45.35 * 0.75


class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(
                name="LegalBody",
                parent=self.styles["Normal"],
                fontSize=10,
                leading=13,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
            )
        )

    def _font_assets_html(self) -> str:
        return """
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Montserrat:wght@400;600&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
            """.strip()

    def _font_family_css(self) -> str:
        return ""

    def _alignment_from_style(self, style_text: str | None) -> int:
        if not style_text:
            return TA_LEFT
        match = re.search(r"text-align\s*:\s*(left|right|center|justify|both)", style_text, re.I)
        if not match:
            return TA_LEFT
        value = match.group(1).lower()
        if value == "center":
            return TA_CENTER
        if value == "right":
            return TA_RIGHT
        if value in {"justify", "both"}:
            return TA_JUSTIFY
        return TA_LEFT

    def _paragraph_style(self, base: ParagraphStyle, style_text: str | None) -> ParagraphStyle:
        style = ParagraphStyle(name=f"{base.name}_dyn", parent=base)
        style.alignment = self._alignment_from_style(style_text)
        return style

    def _extract_base_font_family(self, html_text: str) -> str | None:
        if not html_text:
            return None

        soup = BeautifulSoup(html_text, "html.parser")

        def _clean(value: str | None) -> str | None:
            if not value:
                return None
            cleaned = value.strip().rstrip(";")
            return cleaned or None

        for style_tag in soup.find_all("style"):
            style_text = style_tag.get_text(" ", strip=False) or ""
            match = re.search(r"body\s*\{[^}]*font-family\s*:\s*([^;}\n]+)", style_text, re.I | re.S)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        for tag in soup.find_all(True):
            style_text = tag.get("style", "") or ""
            if not style_text:
                continue
            match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.I)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        for selector in ("body", "html"):
            tag = soup.find(selector)
            if not tag:
                continue
            style_text = tag.get("style", "") or ""
            match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.I)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        return None

    def _split_font_family_values(self, raw_value: str | None) -> list[str]:
        if not raw_value:
            return []

        cleaned = str(raw_value).strip().rstrip(";")
        if not cleaned:
            return []

        parts = [part.strip().strip('"\'') for part in cleaned.split(",")]
        invalid = {
            "serif",
            "sans-serif",
            "monospace",
            "cursive",
            "fantasy",
            "system-ui",
            "emoji",
            "math",
            "fangsong",
            "inherit",
            "initial",
            "unset",
            "revert",
        }
        return [part for part in parts if part and part.lower() not in invalid]

    def _normalize_font_key(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(name or "").lower())

    def _extract_requested_font_families(self, html_text: str, base_font_family: str | None = None) -> list[str]:
        if not html_text:
            return []

        soup = BeautifulSoup(html_text, "html.parser")
        discovered: list[str] = []

        for style_tag in soup.find_all("style"):
            style_text = style_tag.get_text(" ", strip=False) or ""
            for match in re.finditer(r"font-family\s*:\s*([^;}\n]+)", style_text, re.I):
                discovered.extend(self._split_font_family_values(match.group(1)))

        for node in soup.find_all(True):
            style_text = node.get("style", "") or ""
            if not style_text:
                continue
            for match in re.finditer(r"font-family\s*:\s*([^;]+)", style_text, re.I):
                discovered.extend(self._split_font_family_values(match.group(1)))

        if base_font_family:
            discovered.extend(self._split_font_family_values(base_font_family))

        unique: list[str] = []
        seen = set()
        for family in discovered:
            key = family.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(family)
        return unique

    def _font_search_dirs(self) -> list[Path]:
        root = Path(settings.BASE_DIR)
        candidates = [
            root / "app" / "storage" / "fonts",
            root / "app" / "fonts",
            root / "fonts",
        ]
        return [path for path in candidates if path.exists() and path.is_dir()]

    def _guess_font_format(self, suffix: str) -> str:
        ext = str(suffix or "").lower()
        if ext == ".woff2":
            return "woff2"
        if ext == ".woff":
            return "woff"
        if ext == ".otf":
            return "opentype"
        return "truetype"

    def _guess_font_weight_and_style(self, file_stem: str) -> tuple[str, str]:
        stem = file_stem.lower()
        weight = "400"
        style = "normal"

        if any(token in stem for token in ("thin",)):
            weight = "100"
        elif any(token in stem for token in ("extralight", "ultralight")):
            weight = "200"
        elif any(token in stem for token in ("light",)):
            weight = "300"
        elif any(token in stem for token in ("medium",)):
            weight = "500"
        elif any(token in stem for token in ("semibold", "demibold")):
            weight = "600"
        elif any(token in stem for token in ("bold",)):
            weight = "700"
        elif any(token in stem for token in ("extrabold", "ultrabold", "heavy", "black")):
            weight = "800"

        if any(token in stem for token in ("italic", "oblique")):
            style = "italic"

        return weight, style

    def _collect_matching_font_files(self, family_name: str) -> list[Path]:
        if not family_name:
            return []

        # ── 1. YAML registry lookup (primary) ─────────────────────────────
        registry_entry = _find_font_in_registry(family_name)
        if registry_entry:
            if registry_entry.get("system_font", True):
                # Find local .ttf files in storage/fonts/
                target_key = _normalize_name(family_name)
                font_dir = _FONTS_YAML_PATH.parent
                local_files = sorted(
                    [
                        f for f in font_dir.iterdir()
                        if f.is_file()
                        and f.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"}
                        and target_key in _normalize_name(f.stem)
                    ],
                    key=lambda p: str(p).lower(),
                )
                if local_files:
                    return local_files
            else:
                # Google Font — download and cache
                import_url = registry_entry.get("import_url", "")
                if import_url:
                    cached = _download_google_font_ttf(family_name, import_url)
                    if cached:
                        return [cached]

        # ── 2. Filesystem fuzzy scan (fallback) ───────────────────────────
        target_key = self._normalize_font_key(family_name)
        if not target_key:
            return []

        matches: list[Path] = []
        font_exts = {".ttf", ".otf", ".woff", ".woff2"}
        for folder in self._font_search_dirs():
            for file_path in folder.rglob("*"):
                if not file_path.is_file() or file_path.suffix.lower() not in font_exts:
                    continue
                stem_key = self._normalize_font_key(file_path.stem)
                if not stem_key:
                    continue
                if target_key == stem_key or target_key in stem_key or stem_key in target_key:
                    matches.append(file_path)

        return sorted(matches, key=lambda p: str(p).lower())

    def _build_embedded_font_face_css(self, html_text: str, base_font_family: str | None = None) -> str:
        families = self._extract_requested_font_families(html_text, base_font_family)
        if not families:
            return ""

        css_blocks: list[str] = []
        emitted = set()
        matched_families: dict[str, list[str]] = {}
        missing_families: list[str] = []
        for family in families:
            files = self._collect_matching_font_files(family)
            if not files:
                missing_families.append(family)
                continue

            matched_families[family] = [file_path.name for file_path in files]

            for font_file in files:
                try:
                    font_bytes = font_file.read_bytes()
                except Exception:
                    continue

                font_format = self._guess_font_format(font_file.suffix)
                font_weight, font_style = self._guess_font_weight_and_style(font_file.stem)
                signature = (family.lower(), font_weight, font_style, font_file.name.lower())
                if signature in emitted:
                    continue
                emitted.add(signature)

                encoded = base64.b64encode(font_bytes).decode("ascii")
                css_blocks.append(
                    "\n".join(
                        [
                            "@font-face {",
                            f"  font-family: '{family}';",
                            f"  src: url(data:font/{font_format};base64,{encoded}) format('{font_format}');",
                            f"  font-weight: {font_weight};",
                            f"  font-style: {font_style};",
                            "  font-display: swap;",
                            "}",
                        ]
                    )
                )

        # Font diagnostics help verify why a selected frontend font does or
        # does not appear in PDF output.
        if families:
            print(
                "[PDF_FONT_DEBUG]",
                {
                    "requested_families": families,
                    "matched_families": matched_families,
                    "fallback_families": missing_families,
                },
            )

        return "\n\n".join(css_blocks)

    def _is_html_template(self, html_text: str) -> bool:
        return any(token in (html_text or "").lower() for token in ("<html", "<body", "<table", "<div", "<style"))

    def _markup(self, node) -> str:
        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if not isinstance(node, Tag):
            return ""

        name = (node.name or "").lower()
        if name == "br":
            return "<br/>"
        if name in {"strong", "b"}:
            return f"<b>{''.join(self._markup(child) for child in node.children)}</b>"
        if name in {"em", "i"}:
            return f"<i>{''.join(self._markup(child) for child in node.children)}</i>"
        if name == "u":
            return f"<u>{''.join(self._markup(child) for child in node.children)}</u>"
        if name in {"p", "div", "span", "li", "td", "th"}:
            return "".join(self._markup(child) for child in node.children)
        if name in {"table", "tr", "tbody", "thead", "tfoot", "colgroup", "col"}:
            return ""
        return "".join(self._markup(child) for child in node.children)

    def _html_paragraph(self, node, base_style: ParagraphStyle):
        markup = self._markup(node).strip()
        if not markup:
            return None
        return Paragraph(markup, self._paragraph_style(base_style, node.get("style")))

    def _html_image_flowable(self, img_node, max_width=None, max_height=None):
        src = img_node.get("src", "") if hasattr(img_node, "get") else ""
        if not src or not src.startswith("data:") or ";base64," not in src:
            return None

        try:
            header, encoded = src.split(";base64,", 1)
            data = base64.b64decode(encoded)
            reader = ImageReader(io.BytesIO(data))
            iw, ih = reader.getSize()
            if iw <= 0 or ih <= 0:
                return None

            style_text = img_node.get("style", "") if hasattr(img_node, "get") else ""
            requested_width = None
            requested_height = None
            width_match = re.search(r"width\s*:\s*([0-9.]+)px", style_text, re.I)
            height_match = re.search(r"height\s*:\s*([0-9.]+)px", style_text, re.I)
            if width_match:
                requested_width = float(width_match.group(1)) * 72.0 / 96.0
            if height_match:
                requested_height = float(height_match.group(1)) * 72.0 / 96.0

            if requested_width and requested_height:
                iw = requested_width
                ih = requested_height

            scale = 1.0
            if max_width:
                scale = min(scale, max_width / float(iw))
            if max_height:
                scale = min(scale, max_height / float(ih))
            scale = min(scale, 1.0)
            flowable = Image(io.BytesIO(data), width=iw * scale, height=ih * scale)
            flowable.hAlign = "CENTER"
            return flowable
        except Exception:
            return None

    def _html_nodes_to_story(self, nodes, section: str = "body") -> list:
        story = []
        compact = section in {"header", "footer"}
        for node in nodes:
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    story.append(Paragraph(html.escape(text), self.styles["LegalBody"]))
                    if not compact:
                        story.append(Spacer(1, 0.06 * inch))
                continue

            if not isinstance(node, Tag):
                continue

            name = (node.name or "").lower()
            if name == "img":
                image = self._html_image_flowable(node)
                if image is not None:
                    story.append(image)
                    if not compact:
                        story.append(Spacer(1, 0.04 * inch))
                continue

            if name == "table":
                table = self._table_flowable(node)
                if table is not None:
                    story.append(table)
                    if not compact:
                        story.append(Spacer(1, 0.12 * inch))
                continue

            if name in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"}:
                style_text = node.get("style", "") or ""
                if "break-after:page" in style_text or "page-break-after:always" in style_text or "page-break-before:always" in style_text:
                    story.append(PageBreak())
                    continue
                imgs = node.find_all("img", recursive=True)
                if imgs and not node.get_text(" ", strip=True):
                    for img in imgs:
                        image = self._html_image_flowable(
                            img,
                            max_width=(A4[0] - (2 * SIDE_MARGIN_MM * mm)),
                            max_height=28 * mm if name in {"div", "header"} else 22 * mm,
                        )
                        if image is not None:
                            story.append(image)
                            story.append(Spacer(1, 0.02 * inch))
                    continue
                base_style = self.styles["LegalBody"]
                if name == "h3":
                    base_style = ParagraphStyle(
                        name="H3LegalBody",
                        parent=self.styles["LegalBody"],
                        fontSize=11,
                        leading=14,
                        spaceAfter=4,
                    )
                paragraph = self._html_paragraph(node, base_style)
                if paragraph is not None:
                    story.append(paragraph)
                    if not compact:
                        story.append(Spacer(1, 0.06 * inch))
                continue

            if name in {"ul", "ol"}:
                for li in node.find_all("li", recursive=False):
                    paragraph = self._html_paragraph(li, self.styles["LegalBody"])
                    if paragraph is not None:
                        story.append(paragraph)
                        if not compact:
                            story.append(Spacer(1, 0.04 * inch))
                continue

            nested = self._html_nodes_to_story(list(node.children), section=section)
            if nested:
                story.extend(nested)
        return story

    def _extract_html_sections(self, soup):
        root = soup.select_one(".docx-root") or soup.body or soup
        header = root.select_one(":scope > .docx-header, :scope > header")
        content = root.select_one(":scope > .docx-content")
        footer = root.select_one(":scope > .docx-footer, :scope > footer")

        if content is None:
            content = root

        header_nodes = [header] if header is not None else []
        footer_nodes = [footer] if footer is not None else []
        body_nodes = list(content.children) if isinstance(content, Tag) else []
        return header_nodes, body_nodes, footer_nodes

    def _build_html_template_pdf(self, html_text: str) -> io.BytesIO:
        soup = BeautifulSoup(html_text or "", "html.parser")
        header_nodes, body_nodes, footer_nodes = self._extract_html_sections(soup)

        header_html_nodes = [str(node) for node in header_nodes]
        footer_html_nodes = [str(node) for node in footer_nodes]
        body_story = self._html_nodes_to_story(body_nodes, section="body")

        buffer = io.BytesIO()
        page_width, page_height = A4

        header_height = HEADER_HEIGHT_MM * mm
        footer_height = FOOTER_HEIGHT_MM * mm
        side_margin   = SIDE_MARGIN_MM   * mm

        header_frame = Frame(
            x1=0,
            y1=page_height - header_height,
            width=page_width,
            height=header_height,
            leftPadding=side_margin,
            rightPadding=side_margin,
            topPadding=0,
            bottomPadding=2 * mm,
            showBoundary=0,
        )

        body_y      = footer_height
        body_height = page_height - header_height - footer_height

        body_frame = Frame(
            x1=side_margin,
            y1=body_y,
            width=page_width - 2 * side_margin,
            height=body_height,
            leftPadding=0,
            rightPadding=0,
            topPadding=4 * mm,
            bottomPadding=4 * mm,
            showBoundary=0,
        )

        footer_frame = Frame(
            x1=0,
            y1=0,
            width=page_width,
            height=footer_height,
            leftPadding=side_margin,
            rightPadding=side_margin,
            topPadding=2 * mm,
            bottomPadding=2 * mm,
            showBoundary=0,
        )

        def draw_bands(canvas, doc):
            canvas.saveState()
            if header_html_nodes:
                header_soup = BeautifulSoup("".join(header_html_nodes), "html.parser")
                header_story = self._html_nodes_to_story(list(header_soup.contents), section="header")
                header_frame.addFromList(header_story, canvas)
            if footer_html_nodes:
                footer_soup = BeautifulSoup("".join(footer_html_nodes), "html.parser")
                footer_story = self._html_nodes_to_story(list(footer_soup.contents), section="footer")
                footer_frame.addFromList(footer_story, canvas)
            canvas.restoreState()

        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0,
            rightMargin=0,
            topMargin=0,
            bottomMargin=0,
        )
        doc.addPageTemplates([PageTemplate(id="html_notice", frames=[body_frame], onPage=draw_bands)])
        doc.build(body_story)
        buffer.seek(0)
        return buffer

    def _extract_col_widths(self, table_node):
        widths = []
        colgroup = table_node.find("colgroup")
        if not colgroup:
            return widths

        usable_width = A4[0] - 2 * SIDE_MARGIN_MM * mm
        for col in colgroup.find_all("col", recursive=False):
            style = col.get("style", "")
            match = re.search(r"width\s*:\s*([0-9.]+)(px|%)", style, re.I)
            if not match:
                widths.append(None)
                continue
            value = float(match.group(1))
            unit = match.group(2)
            if unit == "%":
                widths.append((value / 100.0) * usable_width)
            else:
                widths.append(value)
        return widths

    def _table_flowable(self, table_node):
        rows = []
        col_widths = self._extract_col_widths(table_node)
        tr_nodes = table_node.find_all("tr", recursive=True)
        if not tr_nodes:
            return None

        table_classes = set(table_node.get("class", []) or [])
        visible_borders = "hidden-table" not in table_classes

        max_cols = 0
        for tr in tr_nodes:
            max_cols = max(max_cols, len(tr.find_all(["td", "th"], recursive=False)))

        if not col_widths and max_cols:
            col_widths = [None] * max_cols

        for tr_idx, tr in enumerate(tr_nodes):
            row = []
            cells = tr.find_all(["td", "th"], recursive=False)
            for cell_idx, cell in enumerate(cells):
                inline_style = cell.get("style", "")
                align = self._alignment_from_style(inline_style)
                if align == TA_LEFT and tr_idx == 0 and cell.name == "th":
                    align = TA_CENTER

                cell_markup = self._markup(cell).strip() or "&nbsp;"
                cell_style = ParagraphStyle(
                    name=f"cell_{tr_idx}_{cell_idx}",
                    parent=self.styles["LegalBody"],
                    alignment=align,
                    spaceAfter=0,
                    leading=12,
                )
                row.append(Paragraph(cell_markup, cell_style))
            rows.append(row)

        table = Table(
            rows,
            colWidths=col_widths if any(col_widths) else None,
            repeatRows=1 if visible_borders and len(rows) > 1 else 0,
        )
        table_style = [
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if visible_borders:
            table_style.append(("GRID", (0, 0), (-1, -1), 0.75, colors.black))
        table.setStyle(TableStyle(table_style))
        return table

    def _find_browser_executable(self) -> str | None:
        candidates = [
            shutil.which("msedge"),
            shutil.which("chrome"),
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            shutil.which("chromium-headless-shell"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _ensure_playwright_chromium(self) -> None:
        browser_cache = os.path.join(settings.BASE_DIR, "app", "storage", "_playwright")
        os.makedirs(browser_cache, exist_ok=True)
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", browser_cache)
        print("PLAYWRIGHT CHROMIUM CHECK")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
            capture_output=True,
        )

    async def _generate_pdf_with_browser_coroutine(
        self,
        page_html: str,
        html_path: str,
        pdf_path: str,
        header_template: str = "",
        footer_template: str = "",
    ) -> None:
        from playwright.async_api import async_playwright

        print("STEP: Using browser renderer")
        print("LAUNCHING PLAYWRIGHT")
        browser_executable = self._find_browser_executable()
        if browser_executable:
            print("USING SYSTEM BROWSER:", browser_executable)
        else:
            self._ensure_playwright_chromium()

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_html)

        async with async_playwright() as playwright:
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--disable-print-preview",
                    "--hide-scrollbars",
                    "--allow-file-access-from-files",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            }
            if browser_executable:
                launch_kwargs["executable_path"] = browser_executable
            browser = await playwright.chromium.launch(**launch_kwargs)
            print("BROWSER STARTED")
            page = await browser.new_page()
            await page.set_content(page_html, wait_until="networkidle")
            await page.evaluate("document.fonts.ready")            
            try:
                await page.evaluate("document.fonts.ready")
            except Exception:
                pass
            print("PAGE LOADED")

            use_header = bool(header_template and header_template.strip())
            use_footer = bool(footer_template and footer_template.strip())

            # ── CRITICAL: Playwright's margin parameter sets the @page margin ──
            # This is what reserves space for header/footer on EVERY page.
            # The bleed offset is added to account for Chromium's internal
            # ~5px top injection into header templates.
            top_margin    = f"{HEADER_HEIGHT_MM}mm" if use_header else "0mm"
            bottom_margin = f"{FOOTER_HEIGHT_MM}mm" if use_footer else "0mm"
            left_margin   = f"{SIDE_MARGIN_MM}mm"
            right_margin  = f"{SIDE_MARGIN_MM}mm"

            print("=" * 60)
            print(f"PDF MARGINS: top={top_margin}, bottom={bottom_margin}")
            print(f"USE_HEADER: {use_header}, USE_FOOTER: {use_footer}")
            print("=" * 60)

            await page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                display_header_footer=use_header or use_footer,
                header_template=header_template if use_header else "<span></span>",
                footer_template=footer_template if use_footer else "<span></span>",
                margin={
                    "top":    top_margin,
                    "bottom": bottom_margin,
                    "left":   left_margin,
                    "right":  right_margin,
                },
            )
            print("PDF GENERATED")
            await browser.close()

    def _generate_pdf_with_browser_worker(
        self,
        body_html: str,
        header_html: str = "",
        footer_html: str = "",
    ) -> io.BytesIO:
        page_html, header_template, footer_template = self._wrap_html_for_print(body_html, header_html, footer_html)

        temp_root = os.path.join(settings.BASE_DIR, "app", "storage", "_pdf_tmp")
        os.makedirs(temp_root, exist_ok=True)

        tmpdir = os.path.join(temp_root, uuid.uuid4().hex)
        os.makedirs(tmpdir, exist_ok=True)
        html_path = os.path.join(tmpdir, "notice.html")
        pdf_path  = os.path.join(tmpdir, "notice.pdf")

        try:
            asyncio.run(
                self._generate_pdf_with_browser_coroutine(
                    page_html, html_path, pdf_path, header_template, footer_template
                )
            )

            if not os.path.exists(pdf_path):
                raise RuntimeError("Playwright did not create the PDF output file.")

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
        except Exception as exc:
            print("STEP: Browser failed with error:", exc)
            raise RuntimeError(f"Browser PDF generation failed: {exc}") from exc
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        use_header = bool(header_template and header_template.strip())
        if use_header:
            pdf_bytes = self._shift_repeating_header_image_up(pdf_bytes)

        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        return buffer

    def _shift_repeating_header_image_up(self, pdf_bytes: bytes) -> bytes:
        # Chromium's print header/footer template mechanism injects a fixed
        # ~5mm top inset into the header band that cannot be cancelled from
        # CSS inside the template (confirmed by testing bleed-compensation
        # values from 0-20mm, standalone rendering, and bundled vs system
        # Chromium - all identical). The only remaining lever is to shift the
        # already-rendered header image back up in the finished PDF itself.
        if not _PYMUPDF_AVAILABLE:
            return pdf_bytes

        top_zone_pt = HEADER_HEIGHT_MM * mm

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    for rect in page.get_image_rects(xref):
                        if rect.y0 >= top_zone_pt:
                            continue
                        # Shift by the image's own measured offset rather than
                        # the nominal bleed constant - Chromium's actual inset
                        # is not exactly round, so snapping straight to 0
                        # eliminates any residual sliver instead of leaving
                        # (actual_offset - nominal_constant) behind.
                        shift_pt = rect.y0
                        new_rect = fitz.Rect(rect.x0, 0, rect.x1, rect.y1 - shift_pt)
                        page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
                        page.insert_image(new_rect, xref=xref, overlay=True, keep_proportion=False)
            shifted_bytes = doc.tobytes()
            doc.close()
            return shifted_bytes
        except Exception as exc:
            print("STEP: Header image shift failed, keeping original PDF:", exc)
            return pdf_bytes

    def _inject_print_styles(
        self,
        html_text: str,
        use_header: bool = False,
        use_footer: bool = False,
        base_font_family: str | None = None,
    ) -> str:
        """
        Inject @page CSS that sets margins on EVERY page — this is the only
        reliable way to keep body content below the header on pages 2, 3, 4 ...

        Playwright's margin parameter alone is NOT enough; it merely sets the
        initial @page margin but the HTML's own @page rule can override it.
        We always write an explicit @page rule here so every page gets the
        correct reserved space.
        """
        soup = BeautifulSoup(html_text, "html.parser")
        head = soup.head
        if head is None:
            html_tag = soup.html
            if html_tag is None:
                html_tag = soup.new_tag("html", attrs={"lang": "en"})
                existing = list(soup.contents)
                for node in existing:
                    html_tag.append(node.extract())
                soup.append(html_tag)
            head = soup.new_tag("head")
            html_tag.insert(0, head)

        top_mm    = HEADER_HEIGHT_MM if use_header else 0
        bottom_mm = FOOTER_HEIGHT_MM if use_footer else 0
        embedded_font_css = self._build_embedded_font_face_css(html_text, base_font_family=base_font_family)
        body_font_css = ""
        if base_font_family:
            body_font_css = f"font-family: {base_font_family} !important;"

        style = soup.new_tag("style")
        style.string = f"""
    {embedded_font_css}

@page {{
  size: A4;
  margin-top: {top_mm}mm;
  margin-bottom: {bottom_mm}mm;
  margin-left: {SIDE_MARGIN_MM}mm;
  margin-right: {SIDE_MARGIN_MM}mm;
}}

* {{
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  box-sizing: border-box;
}}

html, body {{
  margin: 0 !important;
  padding: 0 !important;
}}

.docx-root,
.docx-content,
.pdf-content {{
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
}}

body {{
  margin: 0 !important;
  padding: 0 !important;
    {body_font_css}
}}

p {{
  margin: 0 0 6px 0 !important;
}}

li {{
  margin: 0 0 6px 0 !important;
}}

h1, h2, h3, h4, h5, h6 {{
  margin: 0 0 8px 0 !important;
  page-break-after: avoid;
  break-after: avoid-page;
}}

table {{
  width: 100% !important;
  table-layout: fixed !important;
  word-wrap: break-word !important;
  page-break-inside: auto;
  break-inside: auto;
}}

tr {{
  page-break-inside: avoid;
  break-inside: avoid-page;
  page-break-after: auto;
}}

img {{
  max-width: 100% !important;
  height: auto !important;
}}
""".strip()
        font_assets = BeautifulSoup(self._font_assets_html(), "html.parser")
        for node in reversed(list(font_assets.contents)):
            head.insert(0, node)
        head.append(style)
        return str(soup)

    def _is_valid_header(self, html_text: str) -> bool:
        if not html_text:
            return False
        soup = BeautifulSoup(html_text, "html.parser")
        text = soup.get_text(strip=True)
        if len(text) > 5:
            return True
        if soup.find("img") is not None:
            return True
        return False

    def _has_strong_section_signal(self, node, section: str) -> bool:
        if node is None:
            return False

        text = node.get_text(" ", strip=True) if hasattr(node, "get_text") else ""
        attrs = " ".join(
            str(part)
            for part in [
                getattr(node, "name", "") or "",
                " ".join(node.get("class", []) or []) if hasattr(node, "get") else "",
                node.get("id", "") if hasattr(node, "get") else "",
            ]
        ).lower()

        if section == "header":
            if any(token in attrs for token in ("header", "logo", "masthead")):
                return True
            if node.find(["img", "svg"], recursive=True):
                return True
            return len(text) > 0 and len(text) <= 250 and node.find("img", recursive=True) is not None

        if section == "footer":
            if any(token in attrs for token in ("footer", "seal", "signature")):
                return True
            if node.find(["img", "svg"], recursive=True):
                return True
            return len(text) > 0 and len(text) <= 250 and node.find("img", recursive=True) is not None

        return False

    def _build_playwright_template(
        self,
        content: str,
        band_height: str = f"{HEADER_HEIGHT_MM}mm",
        align_items: str = "flex-start",
        base_font_family: str | None = None,
    ) -> str:
        # Chromium injects ~5px top bleed into header templates.
        # We shift <html> UP by that amount and add padding-top inside
        # the content box so the visible content sits in the correct zone.
        bleed = f"{_CHROMIUM_HEADER_BLEED_MM}mm"
        total_h = f"calc({band_height} + {bleed})"
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
{self._font_family_css()}
<style>
html {{
  margin: -{bleed} 0 0 0 !important;
  padding: 0 !important;
  width: 100%;
  height: {total_h};
  overflow: hidden;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}
body {{
  margin: 0 !important;
  padding: 0 !important;
  width: 100%;
  height: {total_h};
  overflow: hidden;
  font-size: 10px;
  font-family: Arial, sans-serif !important;
}}
.content {{
  width: 100%;
  height: {total_h};
  padding-top: 0;
  box-sizing: border-box;
  display: flex;
  align-items: {align_items};
  justify-content: center;
  text-align: center;
  overflow: hidden;
}}
.content * {{
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}}
p {{ margin: 0 !important; }}
img {{
  max-width: 100%;
  width: auto;
  height: auto;
  max-height: {band_height};
  display: block;
}}
</style>
</head>
<body>
<div class="content">{content}</div>
</body>
</html>"""

    # A real letterhead header/footer (logo + a few lines of address) is a few
    # hundred to a couple thousand characters of actual markup/text. If a
    # <header>/<footer> tag holds far more than that, it almost certainly
    # isn't a real page header/footer — some editors leave the rest of the
    # document nested inside it by mistake. Extracting it whole would squeeze
    # the entire page content into the tiny fixed-height print header/footer
    # band, silently clipping everything that doesn't fit. Treat oversized
    # tags as not-a-header/footer instead.
    #
    # Embedded logo/signature images are shipped as inline base64 data URIs,
    # which can easily run to hundreds of KB of harmless character bulk for a
    # visually tiny image. Counting those bytes against this budget made
    # ordinary letterhead headers look "oversized", got rejected here, and
    # fell through to the much less reliable heuristic search below - which
    # has no size guard at all and can grab a large, wrong chunk of the body.
    # So the budget is measured on the markup with data-URI payloads
    # collapsed, not on the raw character count.
    MAX_HEADER_FOOTER_CHARS = 4000
    _DATA_URI_RE = re.compile(r"data:[^;,\"']+;base64,[^\"'\s]+")

    def _content_length_excluding_data_uris(self, html_text: str) -> int:
        return len(self._DATA_URI_RE.sub("", html_text))

    def _wrap_html_for_print(self, body_html: str, header_html: str = "", footer_html: str = "") -> tuple[str, str, str]:
        """
        Returns (page_html, header_template_html, footer_template_html).
        """
        html_text = body_html or ""
        soup = BeautifulSoup(html_text, "html.parser")
        base_font_family = self._extract_base_font_family(html_text)

        extracted_header = ""
        extracted_footer = ""

        header = soup.find("header")
        footer = soup.find("footer")

        if header is not None:
            header_text = str(header)
            if self._content_length_excluding_data_uris(header_text) <= self.MAX_HEADER_FOOTER_CHARS:
                extracted_header = header_text
                header.extract()

        if footer is not None:
            footer_text = str(footer)
            if self._content_length_excluding_data_uris(footer_text) <= self.MAX_HEADER_FOOTER_CHARS:
                extracted_footer = footer_text
                footer.extract()

        if not header_html:
            header_html = extracted_header

        if not footer_html:
            footer_html = extracted_footer

        if not header_html:
            header_candidates = soup.find_all(
                class_=lambda c: c and any(token in " ".join(c).lower() for token in ("docx-header", "header", "masthead"))
            )
            for candidate in header_candidates:
                if self._has_strong_section_signal(candidate, "header"):
                    header_html = str(candidate)
                    candidate.extract()
                    break

        if not footer_html:
            footer_candidates = soup.find_all(
                class_=lambda c: c and any(token in " ".join(c).lower() for token in ("docx-footer", "footer", "seal"))
            )
            for candidate in footer_candidates:
                if self._has_strong_section_signal(candidate, "footer"):
                    footer_html = str(candidate)
                    candidate.extract()
                    break

        if not header_html or not footer_html:
            body = soup.body or soup
            elements = [el for el in list(body.children) if str(el).strip()]
            for el in elements:
                if not header_html and self._has_strong_section_signal(el, "header"):
                    header_html = str(el)
                    el.extract()
                    continue
                if not footer_html and self._has_strong_section_signal(el, "footer"):
                    footer_html = str(el)
                    el.extract()

        use_header = self._is_valid_header(header_html)
        use_footer = self._is_valid_header(footer_html)

        # KEY: inject @page CSS with correct margins into the page HTML.
        # This ensures EVERY page (not just page 1) reserves space for the header.
        page_html = self._inject_print_styles(
            str(soup),
            use_header=use_header,
            use_footer=use_footer,
            base_font_family=base_font_family,
        )

        header_template = (
            self._build_playwright_template(
                header_html,
                band_height=f"{HEADER_HEIGHT_MM}mm",
                align_items="flex-start",
                base_font_family=base_font_family,
            )
            if use_header else ""
        )
        footer_template = (
            self._build_playwright_template(
                footer_html,
                band_height=f"{FOOTER_HEIGHT_MM}mm",
                align_items="flex-end",
                base_font_family=base_font_family,
            )
            if use_footer else ""
        )

        print("=" * 60)
        print("HEADER FOUND:", bool(header_html), "| LENGTH:", len(header_html))
        print("FOOTER FOUND:", bool(footer_html), "| LENGTH:", len(footer_html))
        print("=" * 60)

        return page_html, header_template, footer_template

    async def _generate_pdf_with_browser(self, body_html: str) -> io.BytesIO:
        return await asyncio.to_thread(self._generate_pdf_with_browser_worker, body_html)

    async def generate_communication_pdf(
        self,
        subject: str,
        body_html: str,
        structured_components: dict = None,
        header: dict = None,
        footer: dict = None,
        signature_block: dict = None,
    ) -> io.BytesIO:
        html_text = body_html or ""
        if self._is_html_template(html_text):
            print("STEP: Enter generate_communication_pdf")
            header_html = ""
            footer_html = ""

            if header:
                parts = []
                if header.get("entity_name"):
                    parts.append(f"<b>{header['entity_name']}</b>")
                if header.get("address"):
                    parts.append(header["address"])
                header_html = "<br/>".join(parts)

            if footer and footer.get("round_seal"):
                footer_html = f"<img src='{footer['round_seal']}' style='height:50px;' />"

            return await asyncio.to_thread(self._generate_pdf_with_browser_worker, html_text, header_html, footer_html)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        story = []

        if header:
            if header.get("entity_name"):
                story.append(Paragraph(f"<b>{header.get('entity_name')}</b>", self.styles["Normal"]))
            if header.get("trust_line"):
                story.append(Paragraph(header.get("trust_line"), self.styles["Normal"]))
            if header.get("address"):
                story.append(Paragraph(header.get("address"), self.styles["Normal"]))
            story.append(Spacer(1, 0.25 * inch))

        soup = BeautifulSoup(body_html or "", "html.parser")
        root = soup.body if soup.body else soup

        for node in root.children:
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    story.append(Paragraph(html.escape(text), self.styles["LegalBody"]))
                    story.append(Spacer(1, 0.08 * inch))
                continue

            if not isinstance(node, Tag):
                continue

            name = (node.name or "").lower()

            if name == "table":
                table = self._table_flowable(node)
                if table is not None:
                    story.append(table)
                    story.append(Spacer(1, 0.18 * inch))
                continue

            if name in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}:
                base_style = self.styles["LegalBody"]
                if name == "h3":
                    base_style = ParagraphStyle(
                        name="H3LegalBody",
                        parent=self.styles["LegalBody"],
                        fontSize=11,
                        leading=14,
                        spaceAfter=4,
                    )
                paragraph = self._html_paragraph(node, base_style)
                if paragraph is not None:
                    story.append(paragraph)
                    story.append(Spacer(1, 0.08 * inch))
                continue

            if name in {"ul", "ol"}:
                for li in node.find_all("li", recursive=False):
                    paragraph = self._html_paragraph(li, self.styles["LegalBody"])
                    if paragraph is not None:
                        story.append(paragraph)
                        story.append(Spacer(1, 0.05 * inch))
                continue

            paragraph = self._html_paragraph(node, self.styles["LegalBody"])
            if paragraph is not None:
                story.append(paragraph)
                story.append(Spacer(1, 0.08 * inch))

        story.append(Spacer(1, 0.6 * inch))

        if signature_block and signature_block.get("signature"):
            try:
                sig_bytes = base64.b64decode(signature_block["signature"].split(",")[1])
                sig = Image(io.BytesIO(sig_bytes))
                sig.drawHeight = AO_SIGNATURE_HEIGHT_PT
                sig.drawWidth = AO_SIGNATURE_WIDTH_PT
                sig.hAlign = "LEFT"
                story.append(sig)
                story.append(Spacer(1, 0.1 * inch))
            except Exception:
                pass

        if signature_block and signature_block.get("ao_name"):
            story.append(Paragraph(f"<b>{signature_block.get('ao_name')}</b>", self.styles["Normal"]))

        if signature_block and signature_block.get("designation"):
            story.append(Paragraph(signature_block.get("designation"), self.styles["Normal"]))

        if footer and footer.get("round_seal"):
            try:
                seal_bytes = base64.b64decode(footer["round_seal"].split(",")[1])
                seal = Image(io.BytesIO(seal_bytes))
                seal.drawHeight = 70
                seal.drawWidth = 70
                seal.hAlign = "CENTER"
                story.append(Spacer(1, 0.3 * inch))
                story.append(seal)
            except Exception:
                pass

        doc.build(story)
        buffer.seek(0)
        return buffer
