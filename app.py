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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# Auth endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    try:
        # Sign up with email redirect disabled to avoid rate limits
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "email_redirect_to": None
            }
        })
        
        if response.user:
            # Check if session is returned (auto-confirmed)
            if response.session:
                return jsonify({
                    "success": True,
                    "message": "Registration successful! You are now logged in.",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email
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
                        "email": response.user.email
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
            return jsonify({
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
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
    """Get the current authenticated user."""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    return jsonify({
        "user": {
            "id": user.id,
            "email": user.email
        }
    })

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
                    # Reset file pointer to beginning for upload
                    file.seek(0)
                    upload_data = file.read()
                    user_client.storage.from_('resumes').upload(
                        path=file_path,
                        file=upload_data,
                        file_options={"content-type": "application/pdf"}
                    )
                except Exception as upload_error:
                    print(f"Storage upload error: {upload_error}")
                    # Continue even if upload fails, but file_path will be null
                    file_path = None

                # 2. Insert into database
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
        
        result = user_client.table('cvs').select('id, filename, created_at, score_data').order('created_at', desc=True).execute()
        
        cvs = []
        for cv in result.data:
            cvs.append({
                "id": cv['id'],
                "filename": cv['filename'],
                "created_at": cv['created_at'],
                "score": cv['score_data'].get('total_score') if cv['score_data'] else None
            })
        
        return jsonify({"success": True, "cvs": cvs})
        
    except Exception as e:
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
        
        result = user_client.table('cvs').select('*').eq('id', cv_id).single().execute()
        
        if result.data:
            # Generate signed URL for the PDF if it exists
            pdf_url = None
            if result.data.get('file_path'):
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
                    "resume_data": result.data['resume_data'],
                    "score_data": result.data['score_data'],
                    "created_at": result.data['created_at'],
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
