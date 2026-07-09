# app/utils/ocr_utils.py
import os
from tempfile import TemporaryDirectory
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
from google.cloud import documentai_v1beta3 as documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account
from app.core.settings import settings


def _docai_ocr(file_path: str) -> str:
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

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=content, mime_type=mime_type),
    )

    result = client.process_document(request=request)
    return result.document.text or ""


def extract_text_with_docai(file_path: str) -> str:
    """
    Industrial OCR method:
    - If PDF → convert fully to images
    - OCR every page with DocAI
    - If image → do enhancement fallback
    """
    suffix = os.path.splitext(file_path)[1].lower()

    # -------------------------------------------------
    # CASE 1 → PDF (convert to images)
    # -------------------------------------------------
    if suffix == ".pdf":
        text_blocks = []

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
                    text_blocks.append(_docai_ocr(img_path))

        return "\n".join(text_blocks)

    # -------------------------------------------------
    # CASE 2 → Image (with enhancement fallback)
    # -------------------------------------------------
    ocr_text = _docai_ocr(file_path)

    if not ocr_text.strip():
        try:
            img = Image.open(file_path)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            enhanced = file_path + "_enhanced.png"
            img.save(enhanced)
            ocr_text = _docai_ocr(enhanced)
            os.remove(enhanced)
        except Exception:
            pass

    return ocr_text
