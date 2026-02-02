# Resume Parser with Mistral OCR

A powerful Streamlit application that uses Mistral's OCR model (`mistral-ocr-2512`) to parse PDF resumes and extract structured data.

## Features

- 📄 **PDF Upload**: Upload resume/CV in PDF format
- 🤖 **Mistral OCR**: Uses `mistral-ocr-2512` model for accurate text extraction
- 📊 **Structured Output**: Extracts data into organized JSON format
- 🎨 **Beautiful UI**: Modern, clean interface with Streamlit
- 📥 **Download**: Export parsed data as JSON

## Extracted Information

The parser extracts the following data from resumes:

- **Personal Info**: Name, Email, Phone, Location, LinkedIn
- **Summary**: Professional summary or objective
- **Experience**: Work history with company, title, duration, responsibilities
- **Education**: Degrees, institutions, field of study, GPA
- **Skills**: Technical, soft skills, programming languages, tools
- **Certifications**: Professional certifications
- **Languages**: Spoken languages with proficiency levels
- **Projects**: Personal or professional projects
- **Awards**: Achievements and recognitions

## Installation

1. **Install Python dependencies**:

   ```bash
   cd /Users/nagarro/Downloads/POC
   pip3 install -r requirements.txt
   ```

## Usage

1. Run the Streamlit app:

   ```bash
   streamlit run resume_parser.py
   ```

2. Open your browser to the displayed URL (usually http://localhost:8501)

3. Upload a PDF resume and click "Parse Resume"

4. View the extracted data in formatted, JSON, or raw text view

5. Download the JSON output if needed

## Requirements

- Python 3.8+
- See `requirements.txt` for Python packages

## Models Used

- **OCR**: `mistral-ocr-2512` - Mistral's dedicated OCR model
- **Structuring**: `mistral-large-latest` - For converting extracted text to structured JSON

## API Key

The application uses the Mistral AI API for OCR and text processing. The API key is already configured in the application.

## Technologies Used

- **Streamlit**: Web application framework
- **Mistral AI**: OCR model (`mistral-ocr-2512`) and LLM for structuring

## License

MIT License
