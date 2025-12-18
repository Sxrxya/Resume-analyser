from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Example job role skill sets
ROLE_SKILLS = {
    "AI Engineer": [
        "Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "NLP", "Data Analysis", "Statistics", "Algorithms", "Model Deployment"
    ],
    "Data Scientist": [
        "Python", "R", "Machine Learning", "Data Visualization", "Statistics",
        "SQL", "Pandas", "Data Cleaning", "Experimentation", "Communication"
    ],
    "Web Developer": [
        "HTML", "CSS", "JavaScript", "React", "Vue", "Node.js", "Flask",
        "Django", "Responsive Design", "APIs"
    ]
}

def simulate_ai(resume_text, job_role):
    """
    Simulated AI logic using keyword matching.
    Extracts skills present in the resume matching the job role.
    Returns extracted skills, match percentage, and suggestions.
    """
    role_skills = ROLE_SKILLS.get(job_role, [])
    resume_lower = resume_text.lower()
    extracted_skills = []

    # Find skills present in the resume
    for skill in role_skills:
        if skill.lower() in resume_lower:
            extracted_skills.append(skill)

    # Calculate match
    match_count = len(extracted_skills)
    total_count = len(role_skills)
    match_percent = round((match_count / total_count) * 100) if total_count else 0

    # Suggestions for missing skills
    missing_skills = [s for s in role_skills if s not in extracted_skills]
    suggestions = []
    if missing_skills:
        suggestions.append(f"Consider highlighting or developing these relevant skills for a {job_role} role: " +
                           ", ".join(missing_skills))
    else:
        suggestions.append("Great! Your resume covers all key skills for this role.")

    # Bonus AI tip
    suggestions.append("Tip: Quantify your achievements, use action verbs, and list specific projects.")

    return {
        "extracted_skills": extracted_skills,
        "match_percent": match_percent,
        "suggestions": suggestions
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    resume_text = data.get('resume', '')
    job_role = data.get('role', '')

    # AI logic: Use OpenAI API here if available
    # For demonstration, we use simulated AI
    result = simulate_ai(resume_text, job_role)

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)