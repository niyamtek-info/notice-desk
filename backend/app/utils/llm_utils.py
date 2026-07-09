import json
from typing import List, Optional
import google.generativeai as genai
import google.generativeai as genai
from app.core.settings import settings
from app.api.v1.schemas.chat_schema import ChatTurn

SYSTEM_PROMPT = (
    "You are an AI assistant specialized in property-based loan applications. "
    "Your role is to help users understand loan eligibility, required documents, "
    "application steps, repayment structures, property evaluation, and compliance checks. "
    "Always provide clear, structured, and easy-to-follow explanations. "
    "Do not provide financial or legal advice; instead, explain processes, guidelines, "
    "and common industry practices in property loans. "
    "If specific financial/legal advice is requested, politely suggest consulting "
    "a qualified financial advisor or legal professional."
)


# Legacy Bedrock/Claude code removed. 
# Using call_gemini for chat functionality.

def call_gemini(message: str, history: Optional[List[ChatTurn]] = None) -> str:
    """Calls Google Gemini AI model for chat."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        import os
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY not found."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Convert history to Gemini format
    gemini_history = []
    if history:
        for turn in history:
            role = turn.role if turn.role == "user" else "model"
            gemini_history.append({"role": role, "parts": [turn.content]})

    chat = model.start_chat(history=gemini_history)
    
    try:
        response = chat.send_message(message)
        if response.text:
            return response.text
        return "Sorry, the model did not return any content."
    except Exception as e:
        print(f"ERROR: Gemini chat failed: {str(e)}")
        return f"Error: {str(e)}"


