# app/utils/ocr_utils.py
import os
from tempfile import TemporaryDirectory
from typing import Optional
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
from google.cloud import documentai_v1beta3 as documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account
from app.core.settings import settings
from app.utils.gemini import detect_document_language

# Maps full language names to the ISO codes Document AI's OCR hints expect,
# for when a caller explicitly overrides detection with a known language.
LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "kannada": "kn",
    "malayalam": "ml",
    "bengali": "bn",
    "gujarati": "gu",
    "marathi": "mr",
    "punjabi": "pa",
}


def _resolve_language_hints(language: Optional[str]) -> Optional[list[str]]:
    """
    Resolve a language (name or ISO code) to a Document AI hint list.
    Returns None when no language is known — Document AI then auto-detects
    the script itself, which is what drives the initial probe pass.
    """
    if not language:
        return None
    key = language.strip().lower()
    code = LANGUAGE_NAME_TO_CODE.get(key, key if len(key) <= 3 else None)
    return [code] if code else None


def _docai_ocr(file_path: str, language_hints: Optional[list[str]] = None) -> str:
    """Send file to Google Document AI for OCR."""
    client_options = ClientOptions(
        api_endpoint=f"{settings.GOOGLE_LOCATION}-documentai.googleapis.com"
    )
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        # Explicit service-account JSON file provided
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS
        )
        client = documentai.DocumentProcessorServiceClient(
            credentials=credentials, client_options=client_options
        )
    else:
        # Use Application Default Credentials (VM attached service account)
        client = documentai.DocumentProcessorServiceClient(
            client_options=client_options
        )

    name = (
        f"projects/{settings.GOOGLE_PROJECT_ID}/locations/"
        f"{settings.GOOGLE_LOCATION}/processors/{settings.GOOGLE_PROCESSOR_ID}"
    )

    mime_type = "application/pdf" if file_path.endswith(".pdf") else "image/png"

    with open(file_path, "rb") as f:
        content = f.read()

    process_options = None
    if language_hints:
        process_options = documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                hints=documentai.OcrConfig.Hints(language_hints=language_hints)
            )
        )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=content, mime_type=mime_type),
        process_options=process_options,
    )

    result = client.process_document(request=request)
    return result.document.text or ""


def extract_text_with_docai(file_path: str, language: Optional[str] = None) -> str:
    """
    Industrial OCR method:
    - If PDF → convert fully to images
    - OCR every page with DocAI
    - If image → do enhancement fallback

    Language handling: an explicit `language` is used as-is when given, but
    normally none is supplied (the UI's language field is not treated as
    source of truth). Instead the document's own language is auto-detected —
    the first page/probe is OCR'd with no hints (Document AI's own script
    auto-detection), its text is handed to Gemini (`detect_document_language`),
    and the detected code becomes the hint for the rest of the document. This
    scales to any language Gemini can recognise without hardcoding a fixed
    list per doc.
    """
    suffix = os.path.splitext(file_path)[1].lower()
    default_hints = _resolve_language_hints(language)

    # -------------------------------------------------
    # CASE 1 → PDF (convert to images)
    # -------------------------------------------------
    if suffix == ".pdf":
        text_blocks = []
        active_hints = default_hints
        detected = bool(language)

        with TemporaryDirectory() as tmpdir:
            try:
                from pdf2image import pdfinfo_from_path
                info = pdfinfo_from_path(file_path, poppler_path=settings.POPPLER_PATH)
                total_pages = info.get("Pages", 1)
            except Exception:
                total_pages = 1

            batch_size = 4
            for start_page in range(1, total_pages + 1, batch_size):
                end_page = min(start_page + batch_size - 1, total_pages)

                # Convert PDF batch into images
                pages = convert_from_path(
                    file_path,
                    dpi=200,
                    first_page=start_page,
                    last_page=end_page,
                    poppler_path=settings.POPPLER_PATH
                )

                for idx, page in enumerate(pages):
                    img_path = os.path.join(tmpdir, f"page_{start_page+idx}.png")
                    page.save(img_path, "PNG")
                    page_text = _docai_ocr(img_path, active_hints)
                    text_blocks.append(page_text)

                    # Detect once, from the first page with real text, then
                    # reuse that language for every remaining page.
                    if not detected and page_text.strip():
                        detected = True
                        detected_lang = detect_document_language(page_text)
                        if detected_lang:
                            active_hints = _resolve_language_hints(detected_lang)

        return "\n".join(text_blocks)

    # -------------------------------------------------
    # CASE 2 → Image (with enhancement fallback)
    # -------------------------------------------------
    ocr_text = _docai_ocr(file_path, default_hints)

    if ocr_text.strip() and not language:
        detected_lang = detect_document_language(ocr_text)
        focused_hints = _resolve_language_hints(detected_lang)
        if focused_hints != default_hints:
            # Re-run once with a focused hint for better accuracy than the
            # unhinted auto-detect pass — cheap for a single image.
            ocr_text = _docai_ocr(file_path, focused_hints) or ocr_text

    if not ocr_text.strip():
        try:
            img = Image.open(file_path)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            enhanced = file_path + "_enhanced.png"
            img.save(enhanced)
            ocr_text = _docai_ocr(enhanced, default_hints)
            os.remove(enhanced)
        except Exception:
            pass

    return ocr_text
