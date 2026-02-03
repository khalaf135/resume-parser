import os
import base64
from mistralai import Mistral

# Initialize Mistral client
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

client = Mistral(api_key=MISTRAL_API_KEY)

def extract_resume_with_ocr(pdf_bytes):
    """Use Mistral OCR to extract text from PDF resume."""
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    
    ocr_response = client.ocr.process(
        model="mistral-ocr-2512",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_base64}"
        },
        include_image_base64=False
    )
    
    all_text = ""
    for page in ocr_response.pages:
        all_text += f"\n--- Page {page.index + 1} ---\n"
        all_text += page.markdown
    
    return all_text
