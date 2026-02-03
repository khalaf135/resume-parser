import os
import json
from mistralai import Mistral

# Initialize Mistral client
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

client = Mistral(api_key=MISTRAL_API_KEY)

def generate_skill_assessment(skill_name, skill_type):
    """Generate skill assessment questions for a specific skill."""
    if skill_type == 'technical':
        prompt = f"""Generate 5 technical assessment questions for the skill: {skill_name}

Create questions that test actual knowledge of {skill_name}. Include:
- Code tracing questions (what does this code output?)
- Debugging questions (find the error)
- Concept questions
- Best practices questions

For programming skills, include actual code snippets to analyze.

Respond with JSON in this exact format:
{{
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "<question with code if applicable>",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "<correct option>",
            "explanation": "<why this is correct>"
        }}
    ]
}}"""
    else:
        prompt = f"""Generate 5 soft skill assessment questions for: {skill_name}

Create scenario-based questions that assess the candidate's {skill_name} abilities.
Present workplace scenarios and ask how they would handle them.

Respond with JSON in this exact format:
{{
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "<scenario-based question>",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "<correct option>",
            "explanation": "<why this is the best approach>"
        }}
    ]
}}"""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def generate_quiz(resume_data):
    """Generate quiz questions from resume content."""
    quiz_prompt = f"""Based on this resume data, generate 7 quiz questions to test if the person actually knows what they claimed on their resume.

Resume Data: {json.dumps(resume_data, indent=2)}

Create questions about:
- Their work experience details
- Technical skills they mentioned
- Projects they worked on
- Their education
- Specific achievements they claimed

Mix question types: multiple choice (4 options, one correct) and true/false.

Respond with JSON in this exact format:
{{
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "<question text>",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "<correct option>",
            "explanation": "<why this is the correct answer>"
        }},
        {{
            "id": 2,
            "type": "true_false",
            "question": "<question text>",
            "correct_answer": "true" or "false",
            "explanation": "<why this is correct>"
        }}
    ]
}}"""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": quiz_prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
