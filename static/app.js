/* ========================================
   Resume Parser - JavaScript Frontend
   ======================================== */

// Global state
let sessionId = localStorage.getItem('sessionId');
let resumeData = null;
let scoreData = null;
let quizQuestions = [];
let currentQuestionIndex = 0;
let userAnswers = {};

// ======== Auth Helper Functions ========
function getAccessToken() {
    return localStorage.getItem('access_token');
}

function isLoggedIn() {
    return !!getAccessToken();
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.reload();
}

function updateAuthUI() {
    const authControls = document.getElementById('authControls');
    if (!authControls) return;

    if (isLoggedIn()) {
        const user = getCurrentUser();
        authControls.innerHTML = `
            <span class="user-email">${user?.email || 'User'}</span>
            <a href="#" class="btn-secondary saved-cvs-link" onclick="window.location.href='/results'">My CVs</a>
            <button class="btn-secondary logout-btn" onclick="logout()">Logout</button>
        `;
    } else {
        authControls.innerHTML = `
            <a href="/login" class="btn-secondary">Login</a>
            <a href="/login#register" class="btn-primary-small">Register</a>
        `;
    }
}

function getAuthHeaders() {
    const token = getAccessToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// ======== Upload Page Logic ========
document.addEventListener('DOMContentLoaded', () => {
    // Update auth UI on all pages
    updateAuthUI();

    const uploadBox = document.getElementById('uploadBox');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (uploadBox) {
        // Click to upload
        uploadBox.addEventListener('click', () => fileInput.click());

        // Drag and drop
        uploadBox.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadBox.classList.add('dragover');
        });

        uploadBox.addEventListener('dragleave', () => {
            uploadBox.classList.remove('dragover');
        });

        uploadBox.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadBox.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length && files[0].type === 'application/pdf') {
                handleFileSelect(files[0]);
            }
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFileSelect(e.target.files[0]);
            }
        });

        // Remove file
        removeFile?.addEventListener('click', () => {
            fileInput.value = '';
            fileInfo.style.display = 'none';
            uploadBox.style.display = 'block';
            analyzeBtn.disabled = true;
        });

        // Analyze button
        analyzeBtn?.addEventListener('click', uploadAndAnalyze);
    }
});

let selectedFile = null;

function handleFileSelect(file) {
    selectedFile = file;
    const uploadBox = document.getElementById('uploadBox');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const analyzeBtn = document.getElementById('analyzeBtn');

    uploadBox.style.display = 'none';
    fileInfo.style.display = 'flex';
    fileName.textContent = file.name;
    analyzeBtn.disabled = false;
}

async function uploadAndAnalyze() {
    if (!selectedFile) return;

    const analyzeBtn = document.getElementById('analyzeBtn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const btnLoading = analyzeBtn.querySelector('.btn-loading');
    const progressSection = document.getElementById('progressSection');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    // Show loading state
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline-flex';
    analyzeBtn.disabled = true;
    progressSection.style.display = 'block';

    // Simulate progress
    const progressSteps = [
        { percent: 20, text: '📄 Uploading PDF...' },
        { percent: 40, text: '🔍 Extracting text with OCR...' },
        { percent: 60, text: '🧠 Analyzing resume structure...' },
        { percent: 80, text: '📊 Calculating score...' },
        { percent: 95, text: '✨ Finalizing results...' }
    ];

    let stepIndex = 0;
    const progressInterval = setInterval(() => {
        if (stepIndex < progressSteps.length) {
            progressFill.style.width = progressSteps[stepIndex].percent + '%';
            progressText.textContent = progressSteps[stepIndex].text;
            stepIndex++;
        }
    }, 1500);

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const headers = getAuthHeaders();
        const response = await fetch('/api/parse', {
            method: 'POST',
            headers: headers,
            body: formData
        });

        clearInterval(progressInterval);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to parse resume');
        }

        const data = await response.json();

        // Store session data
        sessionId = data.session_id;
        localStorage.setItem('sessionId', sessionId);
        localStorage.setItem('resumeData', JSON.stringify(data.resume_data));
        localStorage.setItem('scoreData', JSON.stringify(data.score_data));

        progressFill.style.width = '100%';
        progressText.textContent = '✅ Analysis complete!';

        // Redirect to results
        setTimeout(() => {
            window.location.href = '/results';
        }, 500);

    } catch (error) {
        clearInterval(progressInterval);
        progressFill.style.width = '0%';
        progressText.textContent = '❌ ' + error.message;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
        analyzeBtn.disabled = false;
    }
}

// ======== Results Page Logic ========
function loadResults() {
    resumeData = JSON.parse(localStorage.getItem('resumeData'));
    scoreData = JSON.parse(localStorage.getItem('scoreData'));
    sessionId = localStorage.getItem('sessionId');

    if (!resumeData || !scoreData) {
        window.location.href = '/';
        return;
    }

    // Display total score
    displayTotalScore(scoreData.total_score);
    document.getElementById('overallFeedback').textContent = scoreData.overall_feedback || '';

    // Display category scores
    displayCategoryScore('contentQuality', scoreData.categories.content_quality, 'Content Quality');
    displayCategoryScore('skillsRelevance', scoreData.categories.skills_relevance, 'Skills Relevance');
    displayCategoryScore('experienceClarity', scoreData.categories.experience_clarity, 'Experience Clarity');
    displayCategoryScore('formattingStructure', scoreData.categories.formatting_structure, 'Formatting');

    // Display strengths
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = (scoreData.strengths || []).map(s => `<li>${s}</li>`).join('');

    // Display improvements
    const improvementsList = document.getElementById('improvementsList');
    improvementsList.innerHTML = (scoreData.improvements || []).map(i => `
        <div class="improvement-item">
            <div class="improvement-issue">${i.issue}</div>
            <div class="improvement-suggestion">${i.suggestion}</div>
        </div>
    `).join('');

    // Display resume data
    displayResumeData();

    // Setup download button
    document.getElementById('downloadJson')?.addEventListener('click', downloadJson);

    // Setup quiz button
    document.getElementById('startQuizBtn')?.addEventListener('click', () => {
        window.location.href = '/quiz';
    });
}

function displayTotalScore(score) {
    const scoreValue = document.getElementById('totalScore');
    const scoreFill = document.getElementById('scoreFill');

    scoreValue.textContent = score;

    // Animate the circle
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (score / 100) * circumference;

    setTimeout(() => {
        scoreFill.style.strokeDashoffset = offset;
    }, 100);
}

function displayCategoryScore(elementId, categoryData, name) {
    const element = document.getElementById(elementId);
    if (!element || !categoryData) return;

    const scoreSpan = element.querySelector('.category-score');
    const fillBar = element.querySelector('.category-fill');
    const feedbackP = element.querySelector('.category-feedback');

    scoreSpan.textContent = `${categoryData.score}/25`;
    fillBar.style.width = `${(categoryData.score / 25) * 100}%`;
    feedbackP.textContent = categoryData.feedback || '';
}

function displayResumeData() {
    // Personal Info
    const personalInfo = document.getElementById('personalInfo')?.querySelector('.info-content');
    if (personalInfo && resumeData) {
        personalInfo.innerHTML = `
            ${resumeData.name ? `<p><strong>Name:</strong> ${resumeData.name}</p>` : ''}
            ${resumeData.email ? `<p><strong>Email:</strong> ${resumeData.email}</p>` : ''}
            ${resumeData.phone ? `<p><strong>Phone:</strong> ${resumeData.phone}</p>` : ''}
            ${resumeData.location ? `<p><strong>Location:</strong> ${resumeData.location}</p>` : ''}
            ${resumeData.linkedin ? `<p><strong>LinkedIn:</strong> <a href="${resumeData.linkedin}" target="_blank">Profile</a></p>` : ''}
        `;
    }

    // Summary
    const summaryInfo = document.getElementById('summaryInfo')?.querySelector('.info-content');
    if (summaryInfo) {
        summaryInfo.innerHTML = `<p>${resumeData.summary || 'No summary provided'}</p>`;
    }

    // Experience
    const experienceInfo = document.getElementById('experienceInfo')?.querySelector('.info-content');
    if (experienceInfo && resumeData.experience) {
        experienceInfo.innerHTML = resumeData.experience.map(exp => `
            <div class="exp-item">
                <div class="exp-title">${exp.title || 'Position'}</div>
                <div class="exp-company">${exp.company || 'Company'}</div>
                <div class="exp-duration">${exp.duration || ''}</div>
                ${exp.responsibilities ? `<div class="exp-responsibilities">${Array.isArray(exp.responsibilities) ? exp.responsibilities.map(r => `• ${r}`).join('<br>') : exp.responsibilities}</div>` : ''}
            </div>
        `).join('');
    }

    // Education
    const educationInfo = document.getElementById('educationInfo')?.querySelector('.info-content');
    if (educationInfo && resumeData.education) {
        educationInfo.innerHTML = resumeData.education.map(edu => `
            <div class="edu-item">
                <div class="edu-title">${edu.degree || 'Degree'}</div>
                <div class="edu-institution">${edu.institution || 'Institution'}</div>
                <div class="edu-duration">${edu.duration || ''}</div>
            </div>
        `).join('');
    }

    // Skills
    const skillsInfo = document.getElementById('skillsInfo')?.querySelector('.info-content');
    if (skillsInfo && resumeData.skills) {
        let skillsHtml = '';
        if (typeof resumeData.skills === 'object' && !Array.isArray(resumeData.skills)) {
            Object.entries(resumeData.skills).forEach(([category, skills]) => {
                if (skills && skills.length) {
                    skillsHtml += `<p><strong>${category}:</strong></p><div class="skill-tags">${skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>`;
                }
            });
        } else if (Array.isArray(resumeData.skills)) {
            skillsHtml = `<div class="skill-tags">${resumeData.skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>`;
        }
        skillsInfo.innerHTML = skillsHtml || '<p>No skills listed</p>';
    }
}

function downloadJson() {
    const dataStr = JSON.stringify({ resume: resumeData, score: scoreData }, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resume_analysis.json';
    a.click();
    URL.revokeObjectURL(url);
}

// ======== Quiz Page Logic ========
async function initQuiz() {
    sessionId = localStorage.getItem('sessionId');

    if (!sessionId) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch('/api/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        if (!response.ok) {
            throw new Error('Failed to generate quiz');
        }

        const data = await response.json();
        quizQuestions = data.questions;

        document.getElementById('quizLoading').style.display = 'none';
        document.getElementById('quizContainer').style.display = 'block';

        displayQuestion(0);

    } catch (error) {
        document.getElementById('quizLoading').innerHTML = `
            <p style="color: var(--error);">❌ ${error.message}</p>
            <a href="/results" class="btn-secondary" style="margin-top: 1rem; display: inline-block;">← Back to Results</a>
        `;
    }
}

function displayQuestion(index) {
    if (index < 0 || index >= quizQuestions.length) return;

    currentQuestionIndex = index;
    const question = quizQuestions[index];

    // Update progress
    const progress = ((index + 1) / quizQuestions.length) * 100;
    document.getElementById('quizProgressFill').style.width = `${progress}%`;
    document.getElementById('quizProgressText').textContent = `Question ${index + 1} of ${quizQuestions.length}`;

    // Update question
    document.getElementById('questionNumber').textContent = `Q${index + 1}`;
    document.getElementById('questionText').textContent = question.question;

    // Display options
    const optionsContainer = document.getElementById('optionsContainer');

    if (question.type === 'multiple_choice') {
        optionsContainer.innerHTML = question.options.map((opt, i) => {
            const letter = String.fromCharCode(65 + i);
            const isSelected = userAnswers[question.id] === opt;
            return `
                <button class="option-btn ${isSelected ? 'selected' : ''}" data-answer="${opt}">
                    <span class="option-letter">${letter}</span>
                    <span>${opt}</span>
                </button>
            `;
        }).join('');
    } else {
        optionsContainer.innerHTML = ['True', 'False'].map(opt => {
            const isSelected = userAnswers[question.id]?.toLowerCase() === opt.toLowerCase();
            return `
                <button class="option-btn ${isSelected ? 'selected' : ''}" data-answer="${opt.toLowerCase()}">
                    <span class="option-letter">${opt[0]}</span>
                    <span>${opt}</span>
                </button>
            `;
        }).join('');
    }

    // Add click handlers
    optionsContainer.querySelectorAll('.option-btn').forEach(btn => {
        btn.addEventListener('click', () => selectAnswer(question.id, btn.dataset.answer));
    });

    // Update navigation buttons
    document.getElementById('prevBtn').disabled = index === 0;
    const nextBtn = document.getElementById('nextBtn');
    nextBtn.textContent = index === quizQuestions.length - 1 ? 'Submit' : 'Next →';
    nextBtn.disabled = !userAnswers[question.id];

    // Setup navigation
    document.getElementById('prevBtn').onclick = () => displayQuestion(index - 1);
    document.getElementById('nextBtn').onclick = () => {
        if (index === quizQuestions.length - 1) {
            submitQuiz();
        } else {
            displayQuestion(index + 1);
        }
    };
}

function selectAnswer(questionId, answer) {
    userAnswers[questionId] = answer;

    // Update UI
    document.querySelectorAll('.option-btn').forEach(btn => {
        btn.classList.remove('selected');
        if (btn.dataset.answer === answer) {
            btn.classList.add('selected');
        }
    });

    document.getElementById('nextBtn').disabled = false;
}

async function submitQuiz() {
    try {
        const response = await fetch('/api/evaluate-quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                answers: userAnswers
            })
        });

        if (!response.ok) throw new Error('Failed to evaluate quiz');

        const result = await response.json();
        displayQuizResults(result);

    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function displayQuizResults(result) {
    document.getElementById('quizContainer').style.display = 'none';
    document.getElementById('quizResults').style.display = 'block';

    // Display score
    document.getElementById('quizScoreValue').textContent = `${result.score}%`;
    document.getElementById('quizScoreSummary').textContent =
        `You got ${result.correct} out of ${result.total} correct`;

    // Animate score circle
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (result.score / 100) * circumference;
    setTimeout(() => {
        document.getElementById('quizScoreFill').style.strokeDashoffset = offset;
    }, 100);

    // Display answers review
    const answersReview = document.getElementById('answersReview');
    answersReview.innerHTML = result.results.map(r => `
        <div class="answer-item ${r.is_correct ? 'correct' : 'incorrect'}">
            <div class="answer-question">${r.question}</div>
            <div class="answer-details">
                <div class="answer-your">
                    <span>Your Answer</span>
                    ${r.your_answer || '(No answer)'}
                </div>
                <div class="answer-correct">
                    <span>Correct Answer</span>
                    ${r.correct_answer}
                </div>
            </div>
            <div class="answer-explanation">💡 ${r.explanation}</div>
        </div>
    `).join('');

    // Retake quiz button
    document.getElementById('retakeQuizBtn')?.addEventListener('click', () => {
        userAnswers = {};
        currentQuestionIndex = 0;
        document.getElementById('quizResults').style.display = 'none';
        initQuiz();
    });
}
