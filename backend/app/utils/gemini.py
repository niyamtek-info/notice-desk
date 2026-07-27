import google.generativeai as genai
import os
from app.core.settings import settings

# Without a timeout, a hung Gemini call blocks the Celery worker/task slot
# handling it indefinitely, backing up the whole extraction/translation/
# checklist queue behind it.
GEMINI_REQUEST_TIMEOUT_SECONDS = 120

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
    
    # Using gemini-2.5-flash for speed and reliability
    model = genai.GenerativeModel('gemini-2.5-flash')

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
    # Using the same model family as extraction (assuming 1.5 logic applies even if user wants 2.5 name retained)
    model = genai.GenerativeModel('gemini-2.5-pro')

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