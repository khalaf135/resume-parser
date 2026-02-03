from flask import Flask, request, jsonify, render_template, send_from_directory
import json
import base64
import os
from mistralai import Mistral
from supabase import create_client, Client
from datetime import datetime


app = Flask(__name__)

# Initialize Mistral client (use env var or fallback)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "kORYxfwgU2OlpmMZ7ykKD9r4grLmT5l4")
client = Mistral(api_key=MISTRAL_API_KEY)

# Initialize Supabase client (use env vars or fallback)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qgjrfyvndhusydplqgnp.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFnanJmeXZuZGh1c3lkcGxxZ25wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAwMTk3MzUsImV4cCI6MjA4NTU5NTczNX0.IagPiWX9NCh90cPzefwab6yd3fOjIybyrbhbuGVBaww")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Store session data (in production, use Redis or database)
session_data = {}

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

def get_user_from_token(request):
    """Extract and validate user from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        # Create a new client with the user's token
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.auth.set_session(token, token)
        user = user_client.auth.get_user(token)
        return user.user if user else None
    except Exception:
        return None

def get_authenticated_client(request):
    """Get authenticated Supabase client from request."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, None
    
    access_token = auth_header.split(' ')[1]
    try:
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.auth.set_session(access_token, access_token)
        user = user_client.auth.get_user(access_token)
        return user_client, user.user if user else None
    except Exception:
        return None, None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/skills')
def skills_page():
    return render_template('skills.html')

@app.route('/certificates')
def certificates_page():
    return render_template('certificates.html')

@app.route('/cvs')
def cv_library():
    return render_template('cv_library.html')

@app.route('/recommendations')
def recommendations():
    return render_template('recommendations.html')

@app.route('/employer/dashboard')
def employer_dashboard():
    return render_template('employer_dashboard.html')

@app.route('/employer/search')
def employer_search():
    return render_template('search_candidates.html')

@app.route('/employer/candidate/<user_id>')
def view_candidate(user_id):
    return render_template('view_candidate.html', candidate_id=user_id)

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# Auth endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user with role."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name', '')
    role = data.get('role', 'candidate')  # Default to candidate
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    if role not in ['candidate', 'employer']:
        return jsonify({"error": "Role must be 'candidate' or 'employer'"}), 400
    
    try:
        # Sign up with email redirect disabled to avoid rate limits
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "email_redirect_to": None,
                "data": {
                    "full_name": full_name,
                    "role": role
                }
            }
        })
        
        if response.user:
            # Check if session is returned (auto-confirmed)
            if response.session:
                # Create user role entry
                try:
                    user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                    user_client.auth.set_session(response.session.access_token, response.session.access_token)
                    
                    # Insert role
                    user_client.table('user_roles').insert({
                        "user_id": response.user.id,
                        "role": role
                    }).execute()
                    
                    # Create initial profile
                    if role == 'candidate':
                        user_client.table('candidate_profiles').insert({
                            "user_id": response.user.id,
                            "full_name": full_name
                        }).execute()
                    else:
                        user_client.table('employer_profiles').insert({
                            "user_id": response.user.id,
                            "full_name": full_name
                        }).execute()
                except Exception as profile_error:
                    print(f"Profile creation error: {profile_error}")
                
                return jsonify({
                    "success": True,
                    "message": "Registration successful! You are now logged in.",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "role": role
                    },
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                })
            else:
                return jsonify({
                    "success": True,
                    "message": "Registration successful. Please check your email to verify your account.",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "role": role
                    }
                })
        else:
            return jsonify({"error": "Registration failed"}), 400
            
    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower():
            return jsonify({"error": "Too many attempts. Please wait a few minutes and try again."}), 429
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            return jsonify({"error": "This email is already registered. Please login instead."}), 409
        return jsonify({"error": error_msg}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Log in an existing user."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            # Get user role
            role = 'candidate'  # Default
            try:
                user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                user_client.auth.set_session(response.session.access_token, response.session.access_token)
                role_result = user_client.table('user_roles').select('role').eq('user_id', response.user.id).execute()
                if role_result.data:
                    role = role_result.data[0]['role']
            except Exception as role_error:
                print(f"Role fetch error: {role_error}")
            
            return jsonify({
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "role": role
                },
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        error_message = str(e)
        if "Invalid login credentials" in error_message:
            return jsonify({"error": "Invalid email or password"}), 401
        return jsonify({"error": error_message}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    try:
        supabase.auth.sign_out()
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get the current authenticated user with role."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get role
    role = 'candidate'
    try:
        role_result = user_client.table('user_roles').select('role').eq('user_id', user.id).execute()
        if role_result.data:
            role = role_result.data[0]['role']
    except Exception:
        pass
    
    return jsonify({
        "user": {
            "id": user.id,
            "email": user.email,
            "role": role
        }
    })

# Profile endpoints
@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get current user's profile."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Get role first
        role_result = user_client.table('user_roles').select('role').eq('user_id', user.id).execute()
        role = role_result.data[0]['role'] if role_result.data else 'candidate'
        
        # Get profile based on role
        table = 'candidate_profiles' if role == 'candidate' else 'employer_profiles'
        profile_result = user_client.table(table).select('*').eq('user_id', user.id).execute()
        
        profile = profile_result.data[0] if profile_result.data else {}
        
        return jsonify({
            "success": True,
            "role": role,
            "profile": profile
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    """Update current user's profile."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    
    try:
        # Get role first
        role_result = user_client.table('user_roles').select('role').eq('user_id', user.id).execute()
        role = role_result.data[0]['role'] if role_result.data else 'candidate'
        
        # Update profile based on role using upsert
        table = 'candidate_profiles' if role == 'candidate' else 'employer_profiles'
        
        profile_data = data
        profile_data['user_id'] = user.id
        profile_data['updated_at'] = datetime.now().isoformat()
        
        result = user_client.table(table).upsert(profile_data).execute()
        
        return jsonify({
            "success": True,
            "profile": result.data[0] if result.data else None
        })
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get a specific user's profile (for employers viewing candidates)."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Check if current user is employer
        role_result = user_client.table('user_roles').select('role').eq('user_id', user.id).execute()
        if not role_result.data or role_result.data[0]['role'] != 'employer':
            return jsonify({"error": "Only employers can view candidate profiles"}), 403
        
        # Get target user's profile
        profile_result = user_client.table('candidate_profiles').select('*').eq('user_id', user_id).execute()
        profile = profile_result.data[0] if profile_result.data else {}
        
        # Get target user's skills
        skills_result = user_client.table('skills').select('*').eq('user_id', user_id).execute()
        
        # Get target user's verified certificates
        certs_result = user_client.table('certificates').select('*').eq('user_id', user_id).eq('status', 'verified').execute()
        
        # Get target user's primary CV (just get first CV if is_primary doesn't exist)
        cv_result = user_client.table('cvs').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
        
        return jsonify({
            "success": True,
            "profile": profile,
            "skills": skills_result.data,
            "certificates": certs_result.data,
            "primary_cv": cv_result.data[0] if cv_result.data else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Skills endpoints
@app.route('/api/skills', methods=['GET'])
def get_skills():
    """Get current user's skills."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        result = user_client.table('skills').select('*').eq('user_id', user.id).execute()
        return jsonify({"success": True, "skills": result.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/skills', methods=['POST'])
def add_skill():
    """Add a new skill."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    skill_name = data.get('skill_name')
    skill_type = data.get('skill_type', 'technical')
    
    if not skill_name:
        return jsonify({"error": "Skill name is required"}), 400
    
    try:
        result = user_client.table('skills').insert({
            "user_id": user.id,
            "skill_name": skill_name,
            "skill_type": skill_type
        }).execute()
        
        return jsonify({"success": True, "skill": result.data[0] if result.data else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/skills/<skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    """Delete a skill."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        user_client.table('skills').delete().eq('id', skill_id).eq('user_id', user.id).execute()
        return jsonify({"success": True, "message": "Skill deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/skills/<skill_id>/assess', methods=['POST'])
def assess_skill(skill_id):
    """Start skill assessment - generate questions."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Get the skill
        skill_result = user_client.table('skills').select('*').eq('id', skill_id).eq('user_id', user.id).execute()
        if not skill_result.data:
            return jsonify({"error": "Skill not found"}), 404
        
        skill = skill_result.data[0]
        
        # Generate assessment questions
        assessment = generate_skill_assessment(skill['skill_name'], skill['skill_type'])
        
        # Store in session
        session_id = base64.b64encode(os.urandom(16)).decode('utf-8')
        session_data[session_id] = {
            "skill_id": skill_id,
            "skill_name": skill['skill_name'],
            "assessment": assessment
        }
        
        # Return questions without answers
        safe_questions = []
        for q in assessment.get("questions", []):
            safe_q = {k: v for k, v in q.items() if k not in ["correct_answer", "explanation"]}
            safe_questions.append(safe_q)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "skill_name": skill['skill_name'],
            "questions": safe_questions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/skills/evaluate', methods=['POST'])
def evaluate_skill_assessment():
    """Evaluate skill assessment answers."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    session_id = data.get('session_id')
    answers = data.get('answers', {})
    
    if not session_id or session_id not in session_data:
        return jsonify({"error": "Invalid session"}), 400
    
    session = session_data[session_id]
    assessment = session.get("assessment", {})
    questions = assessment.get("questions", [])
    skill_id = session.get("skill_id")
    
    correct_count = 0
    results = []
    
    for question in questions:
        q_id = str(question["id"])
        user_answer = answers.get(q_id, "")
        correct_answer = question.get("correct_answer", "")
        is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
        
        if is_correct:
            correct_count += 1
        
        results.append({
            "id": question["id"],
            "question": question["question"],
            "your_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation", "")
        })
    
    total = len(questions)
    score = int((correct_count / total) * 100) if total > 0 else 0
    is_verified = score >= 70  # 70% threshold for verification
    
    # Update skill in database
    try:
        user_client.table('skills').update({
            "score": score,
            "is_verified": is_verified,
            "assessed_at": datetime.now().isoformat()
        }).eq('id', skill_id).eq('user_id', user.id).execute()
    except Exception as e:
        print(f"Error updating skill: {e}")
    
    # Clean up session
    del session_data[session_id]
    
    return jsonify({
        "success": True,
        "score": score,
        "correct": correct_count,
        "total": total,
        "is_verified": is_verified,
        "results": results
    })

# Certificates endpoints
@app.route('/api/certificates', methods=['GET'])
def get_certificates():
    """Get current user's certificates."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        result = user_client.table('certificates').select('*').eq('user_id', user.id).order('created_at', desc=True).execute()
        return jsonify({"success": True, "certificates": result.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/certificates', methods=['POST'])
def add_certificate():
    """Add a new certificate."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    
    try:
        result = user_client.table('certificates').insert({
            "user_id": user.id,
            "certificate_name": data.get('certificate_name'),
            "issuing_organization": data.get('issuing_organization'),
            "issue_date": data.get('issue_date'),
            "credential_id": data.get('credential_id'),
            "credential_url": data.get('credential_url'),
            "status": "pending"  # All certificates start as pending
        }).execute()
        
        return jsonify({"success": True, "certificate": result.data[0] if result.data else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/certificates/<cert_id>', methods=['DELETE'])
def delete_certificate(cert_id):
    """Delete a certificate."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        user_client.table('certificates').delete().eq('id', cert_id).eq('user_id', user.id).execute()
        return jsonify({"success": True, "message": "Certificate deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CV endpoints
@app.route('/api/parse', methods=['POST'])
def parse_resume():
    # REQUIRE authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required. Please login first."}), 401
    
    access_token = auth_header.split(' ')[1]
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    cv_title = request.form.get('title', file.filename)
    
    try:
        pdf_bytes = file.read()
        
        # Extract text using OCR
        raw_text = extract_resume_with_ocr(pdf_bytes)
        
        # Structure the data
        resume_data = structure_resume_data(raw_text)
        
        # Score the resume
        score_data = score_resume(resume_data, raw_text)
        
        # Store in session
        session_id = base64.b64encode(os.urandom(16)).decode('utf-8')
        session_data[session_id] = {
            "resume_data": resume_data,
            "score_data": score_data,
            "raw_text": raw_text
        }
        
        # Save to database (user is authenticated)
        cv_id = None
        try:
            # Create authenticated client
            user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            user_client.auth.set_session(access_token, access_token)
            user = user_client.auth.get_user(access_token)
            
            if user and user.user:
                # 1. Upload file to storage
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = "".join([c for c in file.filename if c.isalnum() or c in "._- "]).strip()
                file_path = f"{user.user.id}/{timestamp}_{safe_filename}"
                
                try:
                    # Use the already-read pdf_bytes for upload
                    user_client.storage.from_('resumes').upload(
                        path=file_path,
                        file=pdf_bytes,
                        file_options={"content-type": "application/pdf"}
                    )
                except Exception as upload_error:
                    print(f"Storage upload error: {upload_error}")
                    # Continue even if upload fails, but file_path will be null
                    file_path = None

                # 2. Insert into database (only use columns that exist)
                result = user_client.table('cvs').insert({
                    "user_id": user.user.id,
                    "filename": file.filename,
                    "resume_data": resume_data,
                    "score_data": score_data,
                    "file_path": file_path
                }).execute()
                
                if result.data:
                    cv_id = result.data[0]['id']
        except Exception as db_error:
            print(f"Database/Storage error: {db_error}")

        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "cv_id": cv_id,
            "resume_data": resume_data,
            "score_data": score_data
        })

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cvs', methods=['GET'])
def list_cvs():
    """List all CVs for the authenticated user."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    access_token = auth_header.split(' ')[1]
    
    try:
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.auth.set_session(access_token, access_token)
        user = user_client.auth.get_user(access_token)
        
        if not user or not user.user:
            return jsonify({"error": "Invalid token"}), 401
        
        # Select only columns that are guaranteed to exist
        result = user_client.table('cvs').select('id, filename, created_at, score_data').eq('user_id', user.user.id).order('created_at', desc=True).execute()
        
        cvs = []
        for cv in result.data:
            cvs.append({
                "id": cv['id'],
                "filename": cv['filename'],
                "title": cv.get('title', cv['filename']),
                "created_at": cv['created_at'],
                "score": cv['score_data'].get('total_score') if cv.get('score_data') else None,
                "is_primary": cv.get('is_primary', False),
                "tags": cv.get('tags', [])
            })
        
        return jsonify({"success": True, "cvs": cvs})
        
    except Exception as e:
        print(f"list_cvs error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cvs/<cv_id>', methods=['GET'])
def get_cv(cv_id):
    """Get a specific CV by ID."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    access_token = auth_header.split(' ')[1]
    
    try:
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.auth.set_session(access_token, access_token)
        user = user_client.auth.get_user(access_token)
        
        if not user or not user.user:
            return jsonify({"error": "Invalid token"}), 401
        
        result = user_client.table('cvs').select('*').eq('id', cv_id).execute()
        
        if result.data:
            cv = result.data[0]
            # Generate signed URL for the PDF if it exists
            pdf_url = None
            if cv.get('file_path'):
                try:
                    url_response = user_client.storage.from_('resumes').create_signed_url(
                        result.data['file_path'], 
                        3600 # 1 hour expiry
                    )
                    pdf_url = url_response.get('signedURL')
                except Exception as e:
                    print(f"Error generating signed URL: {e}")

            return jsonify({
                "success": True,
                "cv": {
                    "id": result.data['id'],
                    "filename": result.data['filename'],
                    "title": result.data.get('title', result.data['filename']),
                    "resume_data": result.data['resume_data'],
                    "score_data": result.data['score_data'],
                    "created_at": result.data['created_at'],
                    "is_primary": result.data.get('is_primary', False),
                    "tags": result.data.get('tags', []),
                    "pdf_url": pdf_url
                }
            })

        else:
            return jsonify({"error": "CV not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cvs/<cv_id>', methods=['DELETE'])
def delete_cv(cv_id):
    """Delete a specific CV by ID."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    access_token = auth_header.split(' ')[1]
    
    try:
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.auth.set_session(access_token, access_token)
        user = user_client.auth.get_user(access_token)
        
        if not user or not user.user:
            return jsonify({"error": "Invalid token"}), 401
        
        result = user_client.table('cvs').delete().eq('id', cv_id).execute()
        
        return jsonify({"success": True, "message": "CV deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cvs/<cv_id>/primary', methods=['PUT'])
def set_primary_cv(cv_id):
    """Set a CV as the primary CV."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # First, unset all other CVs as primary
        user_client.table('cvs').update({"is_primary": False}).eq('user_id', user.id).execute()
        
        # Set this CV as primary
        user_client.table('cvs').update({"is_primary": True}).eq('id', cv_id).eq('user_id', user.id).execute()
        
        return jsonify({"success": True, "message": "Primary CV updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Employer endpoints
@app.route('/api/candidates', methods=['GET'])
def search_candidates():
    """Search candidates with filters (for employers)."""
    user_client, user = get_authenticated_client(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        # Check if user is employer
        role_result = user_client.table('user_roles').select('role').eq('user_id', user.id).execute()
        if not role_result.data or role_result.data[0]['role'] != 'employer':
            return jsonify({"error": "Only employers can search candidates"}), 403
        
        # Get filter parameters
        major = request.args.get('major')
        location = request.args.get('location')
        graduation_year = request.args.get('graduation_year')
        experience = request.args.get('experience')
        skills = request.args.getlist('skills')
        min_skill_score = request.args.get('min_skill_score', 0, type=int)
        
        # Build query for candidates
        query = user_client.table('candidate_profiles').select('*')
        
        print(f"DEBUG: Search filters - Major: {major}, Location: {location}, GradYear: {graduation_year}, Exp: {experience}, Skills: {skills}, MinScore: {min_skill_score}")

        if major:
            query = query.ilike('major_specialization', f'%{major}%')
        if location:
            query = query.ilike('location', f'%{location}%')
        if graduation_year:
            try:
                query = query.eq('graduation_year', int(graduation_year))
            except: pass
        if experience:
            query = query.eq('years_of_experience', experience)
        
        candidates_result = query.execute()
        print(f"DEBUG: Found {len(candidates_result.data)} raw candidate profiles matching basic filters")
        
        # Enhance with skills data
        candidates = []
        for candidate in candidates_result.data:
            # Get skills for this candidate
            skills_result = user_client.table('skills').select('*').eq('user_id', candidate['user_id']).execute()
            candidate_skills = skills_result.data
            
            print(f"DEBUG: Candidate {candidate['user_id']} has {len(candidate_skills)} skills")

            # Filter by skills if specified
            if skills:
                candidate_skill_names = [s['skill_name'].lower().strip() for s in candidate_skills]
                match = False
                for s_filter in skills:
                    if s_filter.lower().strip() in candidate_skill_names:
                        match = True
                        break
                if not match:
                    print(f"DEBUG: Candidate {candidate['user_id']} filtered out due to skill mismatch")
                    continue
            
            # Calculate average verified skill score
            verified_skills = [s for s in candidate_skills if s.get('is_verified')]
            avg_score = sum(s['score'] for s in verified_skills) / len(verified_skills) if verified_skills else 0
            
            if avg_score < min_skill_score:
                print(f"DEBUG: Candidate {candidate['user_id']} filtered out due to low score: {avg_score} < {min_skill_score}")
                continue
            
            candidates.append({
                "user_id": candidate['user_id'],
                "full_name": candidate.get('full_name', 'Anonymous'),
                "professional_headline": candidate.get('professional_headline', ''),
                "location": candidate.get('location', ''),
                "years_of_experience": candidate.get('years_of_experience', ''),
                "skills": candidate_skills[:5],  # Top 5 skills
                "average_score": int(avg_score)
            })
        
        return jsonify({"success": True, "candidates": candidates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Quiz endpoints (kept for backward compatibility)
@app.route('/api/quiz', methods=['POST'])
def get_quiz():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in session_data:
        return jsonify({"error": "Invalid session"}), 400
    
    try:
        resume_data = session_data[session_id]["resume_data"]
        quiz_data = generate_quiz(resume_data)
        
        # Store quiz for evaluation
        session_data[session_id]["quiz"] = quiz_data
        
        # Return questions without correct answers
        safe_questions = []
        for q in quiz_data["questions"]:
            safe_q = {k: v for k, v in q.items() if k not in ["correct_answer", "explanation"]}
            safe_questions.append(safe_q)
        
        return jsonify({"success": True, "questions": safe_questions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/evaluate-quiz', methods=['POST'])
def evaluate_quiz():
    data = request.json
    session_id = data.get('session_id')
    answers = data.get('answers', {})
    
    if not session_id or session_id not in session_data:
        return jsonify({"error": "Invalid session"}), 400
    
    if "quiz" not in session_data[session_id]:
        return jsonify({"error": "Quiz not found"}), 400
    
    quiz = session_data[session_id]["quiz"]
    results = []
    correct_count = 0
    
    for question in quiz["questions"]:
        q_id = str(question["id"])
        user_answer = answers.get(q_id, "")
        is_correct = user_answer.lower() == question["correct_answer"].lower()
        
        if is_correct:
            correct_count += 1
        
        results.append({
            "id": question["id"],
            "question": question["question"],
            "your_answer": user_answer,
            "correct_answer": question["correct_answer"],
            "is_correct": is_correct,
            "explanation": question["explanation"]
        })
    
    total = len(quiz["questions"])
    score = int((correct_count / total) * 100) if total > 0 else 0
    
    return jsonify({
        "success": True,
        "score": score,
        "correct": correct_count,
        "total": total,
        "results": results
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
