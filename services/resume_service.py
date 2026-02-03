import os
import json
from mistralai import Mistral

# Initialize Mistral client
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

client = Mistral(api_key=MISTRAL_API_KEY)

def structure_resume_data(raw_text):
    """Use Mistral LLM to structure the extracted text into JSON."""
    structure_prompt = """Analyze the following resume/CV text and extract the information into a structured JSON format.

Extract the following fields (use null if not found):
- name: Full name of the candidate
- email: Email address
- phone: Phone number
- location: City, Country or full address
- linkedin: LinkedIn profile URL
- summary: Professional summary or objective
- experience: Array of work experiences, each with company, title, duration, location, responsibilities
- education: Array of educational qualifications with institution, degree, field, duration, gpa
- skills: Object with technical, soft, languages (programming), tools arrays
- certifications: Array of certifications with name and date
- languages: Array of spoken languages with proficiency
- projects: Array of projects with name and description

Resume Text:
"""
    
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": structure_prompt + raw_text + "\n\nRespond ONLY with valid JSON."}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def score_resume(resume_data, raw_text):
    """Score the resume out of 100 with detailed breakdown."""
    score_prompt = f"""Analyze this resume and provide a detailed score out of 100.

Resume Data: {json.dumps(resume_data, indent=2)}

Score the resume in these 4 categories (25 points each):

1. **Content Quality (0-25)**: Professional summary quality, quantified achievements, action verbs, metrics
2. **Skills Relevance (0-25)**: Technical skills relevance, industry keywords, skill organization
3. **Experience Clarity (0-25)**: Clear job descriptions, career progression, responsibilities clarity
4. **Formatting & Structure (0-25)**: Completeness, organization, section balance

Respond with JSON in this exact format:
{{
    "total_score": <number 0-100>,
    "categories": {{
        "content_quality": {{
            "score": <0-25>,
            "feedback": "<specific feedback>"
        }},
        "skills_relevance": {{
            "score": <0-25>,
            "feedback": "<specific feedback>"
        }},
        "experience_clarity": {{
            "score": <0-25>,
            "feedback": "<specific feedback>"
        }},
        "formatting_structure": {{
            "score": <0-25>,
            "feedback": "<specific feedback>"
        }}
    }},
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "improvements": [
        {{"issue": "<issue>", "suggestion": "<how to fix>"}},
        {{"issue": "<issue>", "suggestion": "<how to fix>"}},
        {{"issue": "<issue>", "suggestion": "<how to fix>"}}
    ],
    "overall_feedback": "<2-3 sentence overall assessment>"
}}"""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": score_prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
