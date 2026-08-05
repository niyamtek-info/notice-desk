import google.generativeai as genai
import os
from typing import Optional
from app.core.settings import settings

# Without a timeout, a hung Gemini call blocks the Celery worker/task slot
# handling it indefinitely, backing up the whole extraction/translation/
# checklist queue behind it.
GEMINI_REQUEST_TIMEOUT_SECONDS = 120


def detect_document_language(sample_text: str) -> Optional[str]:
    """
    Asks Gemini to identify the dominant language of OCR'd text and returns
    its ISO 639-1/639-2 code (e.g. "hi", "te", "ta", "en").

    This lets OCR language hints scale to any language Gemini can recognise
    instead of being pinned to a fixed list or a UI-selected value — callers
    use the detected code as a Document AI hint for the rest of the document.
    Returns None on any failure so callers can fall back to unhinted
    (auto-detected) OCR rather than breaking extraction.
    """
    sample = (sample_text or "").strip()
    if not sample:
        return None

    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.1-flash-lite')

    prompt = (
        "Identify the dominant language of the text below.\n"
        "Respond with ONLY its ISO 639-1 two-letter code (e.g. hi, ta, te, kn, "
        "ml, bn, gu, mr, pa, en). No explanation, no punctuation — just the code.\n\n"
        f"TEXT:\n{sample[:1500]}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=10,
            ),
            request_options={"timeout": 20},
        )
        code = "".join(ch for ch in (response.text or "").strip().lower() if ch.isalpha())
        return code[:3] or None
    except Exception as e:
        print(f"WARNING: Gemini language detection failed: {e}")
        return None


def call_gemini_ai(prompt, ocr_text=None):
    """
    Calls Google Gemini AI model to process the prompt.
    If ocr_text is provided, it replaces {{ocr_text}} in the prompt.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        # Fallback to env if settings doesn't have it yet or is not reloaded
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in settings or environment variables.")

    genai.configure(api_key=api_key)
    
    # Using gemini-3.1-flash-lite for speed and reliability
    model = genai.GenerativeModel('gemini-3.1-flash-lite')

    if ocr_text is not None:
        prompt = prompt.replace("{{ocr_text}}", ocr_text)

    print("DEBUG: Invoking Gemini AI...")
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.01,
                top_p=1,
                max_output_tokens=30000,
                response_mime_type="application/json",
            ),
            request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
        )
        
        if response.text:
            return response.text
        else:
            print("WARNING: Gemini AI returned empty content.")
            return ""
    except Exception as e:
        print(f"ERROR: Gemini AI call failed: {str(e)}")
        raise

def repair_json_with_llm(malformed_json):
    """
    Uses Gemini AI to repair a malformed JSON string.
    Uses the specialized prompt provided by the user.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    genai.configure(api_key=api_key)
    # Using the same model as extraction for consistency
    model = genai.GenerativeModel('gemini-3.1-flash-lite')

    repair_prompt = f"""FIX THIS MALFORMED JSON. 
YOU ARE A JSON REPAIR ENGINE. 
YOUR ONLY OUTPUT MUST BE THE CORRECTED, STRICTLY VALID JSON.

RULES:
1. Fix missing commas, unquoted keys, and balanced braces.
2. CRITICAL: If the JSON is TRUNCATED (ends abruptly), YOU MUST AUTO-COMPLETE IT to form a valid JSON structure.
   - Close any open strings with a quote.
   - Close any open arrays/objects with ] or }}.
3. DO NOT ADD NEW FIELDS.
4. DO NOT REMOVE EXISTING DATA.
5. RETURN ONLY THE JSON. NO MARKDOWN. NO COMMENTS.

MALFORMED INPUT:
{malformed_json}

CORRECTED JSON:"""

    try:
        response = model.generate_content(
            repair_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=30000,
                response_mime_type="application/json",
            ),
            request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
        )
        return response.text.strip() if response.text else malformed_json
    except Exception as e:
        print(f"ERROR: LLM-based JSON repair failed: {str(e)}")
        return malformed_json