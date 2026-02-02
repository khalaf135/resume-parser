import streamlit as st
import json
import base64
import tempfile
import os
from pathlib import Path
from mistralai import Mistral

# Set page configuration
st.set_page_config(
    page_title="Resume Parser - Mistral OCR",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        color: #6c757d;
        text-align: center;
        margin-bottom: 2rem;
    }
    .json-container {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .dark-card {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        color: white;
    }
    .skill-tag {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        font-size: 0.85rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #4a5568;
        border-bottom: 2px solid #667eea;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Mistral client
@st.cache_resource
def get_mistral_client():
    api_key = "kORYxfwgU2OlpmMZ7ykKD9r4grLmT5l4"
    return Mistral(api_key=api_key)

def extract_resume_with_ocr(client, pdf_bytes, filename="resume.pdf"):
    """Use Mistral OCR (mistral-ocr-2512) to extract text from PDF resume."""
    
    # Encode PDF to base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    
    # Use the Mistral OCR API with mistral-ocr-2512 model
    # Using data URI format for base64 PDF
    ocr_response = client.ocr.process(
        model="mistral-ocr-2512",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_base64}"
        },
        include_image_base64=False
    )
    
    # Extract markdown text from all pages
    all_text = ""
    for page in ocr_response.pages:
        all_text += f"\n--- Page {page.index + 1} ---\n"
        all_text += page.markdown
    
    return all_text, ocr_response

def structure_resume_data(client, raw_text):
    """Use Mistral LLM to structure the extracted text into JSON."""
    
    structure_prompt = """Analyze the following resume/CV text and extract the information into a structured JSON format.

Extract the following fields (use null if not found):
- name: Full name of the candidate
- email: Email address
- phone: Phone number
- location: City, Country or full address
- linkedin: LinkedIn profile URL
- summary: Professional summary or objective
- experience: Array of work experiences, each with:
  - company: Company name
  - title: Job title
  - duration: Time period (e.g., "Jan 2020 - Present")
  - location: Job location
  - responsibilities: Array of key responsibilities/achievements
- education: Array of educational qualifications, each with:
  - institution: School/University name
  - degree: Degree name
  - field: Field of study
  - duration: Time period
  - gpa: GPA if mentioned
- skills: Object with categorized skills:
  - technical: Array of technical skills
  - soft: Array of soft skills
  - languages: Array of programming languages
  - tools: Array of tools/software
- certifications: Array of certifications with name and date
- languages: Array of spoken languages with proficiency level
- projects: Array of projects with name and description
- awards: Array of awards/achievements
- publications: Array of publications if any
- references: Array of references if mentioned

Resume Text:
"""
    
    structure_response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "user",
                "content": structure_prompt + raw_text + "\n\nRespond ONLY with valid JSON, no additional text or markdown."
            }
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        return json.loads(structure_response.choices[0].message.content)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        content = structure_response.choices[0].message.content
        # Clean up common issues
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())

def display_resume_data(data):
    """Display extracted resume data in a beautiful format."""
    
    # Header with name and contact
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if data.get("name"):
            st.markdown(f"## 👤 {data['name']}")
        
        contact_parts = []
        if data.get("email"):
            contact_parts.append(f"📧 {data['email']}")
        if data.get("phone"):
            contact_parts.append(f"📱 {data['phone']}")
        if data.get("location"):
            contact_parts.append(f"📍 {data['location']}")
        if data.get("linkedin"):
            contact_parts.append(f"🔗 [LinkedIn]({data['linkedin']})")
        
        if contact_parts:
            st.markdown(" | ".join(contact_parts))
    
    # Summary
    if data.get("summary"):
        st.markdown("---")
        st.markdown("### 📝 Professional Summary")
        st.info(data["summary"])
    
    # Two column layout for main content
    col1, col2 = st.columns(2)
    
    with col1:
        # Experience
        if data.get("experience"):
            st.markdown("### 💼 Work Experience")
            for exp in data["experience"]:
                with st.expander(f"**{exp.get('title', 'Position')}** at {exp.get('company', 'Company')}", expanded=True):
                    if exp.get("duration"):
                        st.caption(f"🗓️ {exp['duration']}")
                    if exp.get("location"):
                        st.caption(f"📍 {exp['location']}")
                    if exp.get("responsibilities"):
                        for resp in exp["responsibilities"]:
                            st.markdown(f"• {resp}")
        
        # Projects
        if data.get("projects"):
            st.markdown("### 🚀 Projects")
            for project in data["projects"]:
                if isinstance(project, dict):
                    st.markdown(f"**{project.get('name', 'Project')}**")
                    if project.get("description"):
                        st.markdown(project["description"])
                else:
                    st.markdown(f"• {project}")
    
    with col2:
        # Education
        if data.get("education"):
            st.markdown("### 🎓 Education")
            for edu in data["education"]:
                with st.expander(f"**{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')}", expanded=True):
                    if edu.get("field"):
                        st.markdown(f"📚 {edu['field']}")
                    if edu.get("duration"):
                        st.caption(f"🗓️ {edu['duration']}")
                    if edu.get("gpa"):
                        st.markdown(f"📊 GPA: {edu['gpa']}")
        
        # Skills
        if data.get("skills"):
            st.markdown("### 🛠️ Skills")
            skills = data["skills"]
            
            if isinstance(skills, dict):
                if skills.get("technical"):
                    st.markdown("**Technical Skills:**")
                    skill_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in skills["technical"]])
                    st.markdown(skill_html, unsafe_allow_html=True)
                
                if skills.get("languages"):
                    st.markdown("**Programming Languages:**")
                    skill_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in skills["languages"]])
                    st.markdown(skill_html, unsafe_allow_html=True)
                
                if skills.get("tools"):
                    st.markdown("**Tools & Software:**")
                    skill_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in skills["tools"]])
                    st.markdown(skill_html, unsafe_allow_html=True)
                
                if skills.get("soft"):
                    st.markdown("**Soft Skills:**")
                    skill_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in skills["soft"]])
                    st.markdown(skill_html, unsafe_allow_html=True)
            elif isinstance(skills, list):
                skill_html = " ".join([f'<span class="skill-tag">{s}</span>' for s in skills])
                st.markdown(skill_html, unsafe_allow_html=True)
        
        # Certifications
        if data.get("certifications"):
            st.markdown("### 📜 Certifications")
            for cert in data["certifications"]:
                if isinstance(cert, dict):
                    cert_name = cert.get('name', str(cert))
                    cert_date = cert.get('date', '')
                    date_str = f"({cert_date})" if cert_date else ""
                    st.markdown(f"• **{cert_name}** {date_str}")
                else:
                    st.markdown(f"• {cert}")
        
        # Languages
        if data.get("languages"):
            st.markdown("### 🌍 Languages")
            for lang in data["languages"]:
                if isinstance(lang, dict):
                    st.markdown(f"• {lang.get('name', lang)} - {lang.get('proficiency', '')}")
                else:
                    st.markdown(f"• {lang}")

def main():
    # Header
    st.markdown('<h1 class="main-header">📄 Resume Parser with AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload your resume/CV in PDF format and let AI extract all the important information</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        st.markdown("---")
        st.markdown("### 📋 Supported Formats")
        st.markdown("• PDF files")
        st.markdown("---")
        st.markdown("### 🤖 Model Used")
        st.markdown("**OCR:** `mistral-ocr-2512`")
        st.markdown("**Structuring:** `mistral-large-latest`")
        st.markdown("---")
        st.markdown("### ℹ️ How it works")
        st.markdown("""
        1. Upload your resume PDF
        2. Mistral OCR extracts text
        3. Information is structured into JSON
        4. View formatted results
        """)
        st.markdown("---")
        st.markdown("### 🔒 Privacy")
        st.markdown("Your files are processed securely and not stored permanently.")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Resume/CV (PDF)",
        type=["pdf"],
        help="Upload a PDF file containing a resume or CV"
    )
    
    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            process_button = st.button("🔍 Parse Resume", use_container_width=True)
        
        if process_button:
            with st.spinner("🔄 Processing your resume..."):
                try:
                    # Initialize client
                    client = get_mistral_client()
                    
                    # Read PDF bytes
                    pdf_bytes = uploaded_file.read()
                    
                    # Step 1: OCR extraction using mistral-ocr-2512
                    st.info("🔍 Extracting text using Mistral OCR (mistral-ocr-2512)...")
                    raw_text, ocr_response = extract_resume_with_ocr(client, pdf_bytes, uploaded_file.name)
                    
                    st.success(f"✅ Extracted text from {len(ocr_response.pages)} page(s)")
                    
                    # Step 2: Structure the data
                    st.info("🤖 Structuring data with AI...")
                    resume_data = structure_resume_data(client, raw_text)
                    
                    st.success("✅ Resume parsed successfully!")
                    
                    # Store in session state
                    st.session_state["resume_data"] = resume_data
                    st.session_state["raw_text"] = raw_text
                    
                except Exception as e:
                    st.error(f"❌ Error processing resume: {str(e)}")
                    st.exception(e)
    
    # Display results if available
    if "resume_data" in st.session_state:
        st.markdown("---")
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Formatted View", "📝 JSON Output", "📄 Raw Text"])
        
        with tab1:
            display_resume_data(st.session_state["resume_data"])
        
        with tab2:
            st.markdown("### JSON Output")
            json_str = json.dumps(st.session_state["resume_data"], indent=2, ensure_ascii=False)
            st.code(json_str, language="json")
            
            # Download button
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="resume_data.json",
                mime="application/json"
            )
        
        with tab3:
            st.markdown("### Extracted Raw Text (from OCR)")
            st.text_area("Raw OCR Text", st.session_state["raw_text"], height=400)

if __name__ == "__main__":
    main()
