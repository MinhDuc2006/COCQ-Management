import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_with_gemini(file_path):
    """
    Uses Google Gemini 2.0 Flash to extract Serial Number and Date from a PDF.
    Returns: { "date": str or None, "serial_number": List[str] }
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.warning("GOOGLE_API_KEY not found in .env. AI extraction skipped.")
        return None

    try:
        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.0-flash-exp"

        # Reading file bytes
        file_size = os.path.getsize(file_path)
        logging.info(f"Processing PDF for AI extraction: {file_path} ({file_size / 1024:.1f} KB)")
        
        with open(file_path, "rb") as f:
            pdf_data = f.read()

        # Enhanced prompt for scanned/photo PDFs
        prompt = """
        You are a specialized document OCR agent for CO (Certificate of Origin) and CQ (Certificate of Quality).
        Your task is to extract exact metadata from the provided PDF, which may be a scanned photo, blurry, or low-quality.

        Search for:
        1. Date: The document issue date or certificate date. Format as YYYY-MM-DD.
        2. Serial Numbers: Any identifying numbers like Lot No, Serial No, Heat No, Certificate No.
           - Extract the full value.
           - If it's for a specific component (e.g., Tube, Steel, Plate), format it as "Value (Component)".
        
        CRITICAL: 
        - If the text is rotated or blurry, do your best to read it.
        - Only return data you are confident in. Use null if not found.
        - Return ONLY a JSON object with keys "date" and "serial_number" (list of strings).
        """

        logging.info(f"Calling Gemini API for {file_path}...")
        response = client.models.generate_content(
            model=model_id,
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        import json
        if response and response.text:
            logging.info(f"Gemini response received for {file_path}")
            cleaned_text = response.text.strip()
            # Handle markdown wrapping if it exists
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:-3].strip()
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:-3].strip()
            
            try:
                data = json.loads(cleaned_text)
                return {
                    "date": data.get("date"),
                    "serial_number": data.get("serial_number", [])
                }
            except json.JSONDecodeError as je:
                logging.error(f"JSON Decode Error for {file_path}: {je}. Raw: {cleaned_text}")
                return None
        else:
            logging.warning(f"Gemini returned empty response for {file_path}")
            return None

    except Exception as e:
        logging.error(f"Error in Gemini extraction for {file_path}: {e}")
        return None

    return None
