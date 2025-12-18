from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import PyPDF2
import os
import json
from datetime import datetime
import re
from collections import Counter
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import spacy
from textblob import TextBlob
import numpy as np

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Warning: spacy model not loaded. Install with: python -m spacy download en_core_web_sm")
    nlp = None

# ==================== UTILITY FUNCTIONS ====================

def extract_text_from_pdf(file_path):
    """Extract text from PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
    return text

def extract_text_from_txt(file_path):
    """Extract text from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file: {e}")
        return ""

def extract_contact_info(text):
    """Extract contact information from resume text."""
    contact = {
        'email': None,
        'phone': None,
        'linkedin': None,
        'github': None
    }
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email = re.findall(email_pattern, text)
    if email:
        contact['email'] = email[0]
    
    # Phone pattern
    phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone = re.findall(phone_pattern, text)
    if phone:
        contact['phone'] = phone[0]
    
    # LinkedIn pattern
    linkedin_pattern = r'linkedin\.com/in/[\w-]+'
    linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
    if linkedin:
        contact['linkedin'] = linkedin[0]
    
    # GitHub pattern
    github_pattern = r'github\.com/[\w-]+'
    github = re.findall(github_pattern, text, re.IGNORECASE)
    if github:
        contact['github'] = github[0]
    
    return contact

def extract_skills(text):
    """Extract skills from resume text."""
    # Common technical skills
    skills_keywords = [
        'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
        'golang', 'rust', 'typescript', 'scala', 'r', 'matlab', 'perl', 'bash', 'shell',
        'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django',
        'flask', 'spring', 'asp.net', 'rails', 'laravel', 'tensorflow', 'pytorch',
        'scikit-learn', 'pandas', 'numpy', 'sql', 'mongodb', 'postgresql', 'mysql',
        'oracle', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'jenkins', 'git',
        'machine learning', 'deep learning', 'nlp', 'computer vision', 'data analysis',
        'data science', 'big data', 'spark', 'hadoop', 'agile', 'scrum', 'jira',
        'linux', 'unix', 'windows', 'devops', 'microservices', 'rest', 'graphql',
        'api', 'xml', 'json', 'elasticsearch', 'redis', 'rabbitmq', 'kafka'
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skills_keywords:
        if re.search(r'\b' + skill + r'\b', text_lower):
            found_skills.append(skill)
    
    return list(set(found_skills))

def extract_experience(text):
    """Extract work experience from resume."""
    # Look for common date patterns and job titles
    experience = []
    
    # Pattern for dates
    date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*(\d{4})?'
    
    # Common job titles
    job_titles = [
        'developer', 'engineer', 'manager', 'analyst', 'consultant', 'architect',
        'coordinator', 'specialist', 'lead', 'director', 'senior', 'junior',
        'intern', 'associate', 'supervisor', 'administrator', 'scientist'
    ]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(title in line_lower for title in job_titles):
            experience.append({
                'position': line.strip(),
                'line_number': i
            })
    
    return experience

def extract_education(text):
    """Extract education information from resume."""
    education = []
    
    # Degree patterns
    degree_patterns = {
        'bachelor': r'\b(b\.?s\.?|b\.?a\.?|bachelor|undergraduate)',
        'master': r'\b(m\.?s\.?|m\.?a\.?|master|graduate)',
        'phd': r'\b(ph\.?d\.?|doctorate)',
        'diploma': r'\bdiploma\b',
        'certificate': r'\bcertificate\b'
    }
    
    text_lower = text.lower()
    for degree_type, pattern in degree_patterns.items():
        if re.search(pattern, text_lower):
            education.append(degree_type.capitalize())
    
    return education

def calculate_readability(text):
    """Calculate readability metrics using Flesch-Kincaid Grade Level."""
    if not text:
        return {}
    
    sentences = len(re.split(r'[.!?]+', text))
    words = len(text.split())
    
    if sentences == 0 or words == 0:
        return {'grade_level': 0, 'complexity': 'Unknown'}
    
    # Flesch-Kincaid Grade Level
    syllables = sum([count_syllables(word) for word in text.split()])
    grade_level = (0.39 * (words / sentences)) + (11.8 * (syllables / words)) - 15.59
    grade_level = max(0, grade_level)
    
    if grade_level < 6:
        complexity = 'Very Easy'
    elif grade_level < 9:
        complexity = 'Easy'
    elif grade_level < 12:
        complexity = 'Standard'
    elif grade_level < 14:
        complexity = 'Fairly Difficult'
    else:
        complexity = 'Difficult'
    
    return {
        'grade_level': round(grade_level, 2),
        'complexity': complexity,
        'word_count': words,
        'sentence_count': sentences,
        'avg_words_per_sentence': round(words / sentences, 2) if sentences > 0 else 0
    }

def count_syllables(word):
    """Estimate syllable count in a word."""
    word = word.lower()
    syllable_count = 0
    vowels = 'aeiouy'
    previous_was_vowel = False
    
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not previous_was_vowel:
            syllable_count += 1
        previous_was_vowel = is_vowel
    
    if word.endswith('e'):
        syllable_count -= 1
    if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
        syllable_count += 1
    
    return max(1, syllable_count)

def analyze_resume(text):
    """Comprehensive resume analysis."""
    analysis = {
        'contact_info': extract_contact_info(text),
        'skills': extract_skills(text),
        'experience': extract_experience(text),
        'education': extract_education(text),
        'readability': calculate_readability(text),
        'length': len(text),
        'word_count': len(text.split()),
        'analysis_timestamp': datetime.now().isoformat()
    }
    return analysis

def compare_resumes(text1, text2):
    """Compare two resumes and provide insights."""
    analysis1 = analyze_resume(text1)
    analysis2 = analyze_resume(text2)
    
    # Extract skills from both
    skills1 = set(analysis1['skills'])
    skills2 = set(analysis2['skills'])
    
    common_skills = skills1.intersection(skills2)
    unique_to_first = skills1 - skills2
    unique_to_second = skills2 - skills1
    
    comparison = {
        'resume1': {
            'skills_count': len(skills1),
            'experience_count': len(analysis1['experience']),
            'education': analysis1['education'],
            'readability_score': analysis1['readability']
        },
        'resume2': {
            'skills_count': len(skills2),
            'experience_count': len(analysis2['experience']),
            'education': analysis2['education'],
            'readability_score': analysis2['readability']
        },
        'comparison': {
            'common_skills': list(common_skills),
            'unique_to_resume1': list(unique_to_first),
            'unique_to_resume2': list(unique_to_second),
            'skills_overlap_percentage': round((len(common_skills) / max(len(skills1), len(skills2)) * 100), 2) if max(len(skills1), len(skills2)) > 0 else 0
        }
    }
    
    return comparison

def estimate_salary(analysis):
    """Estimate salary based on resume analysis."""
    base_salary = 50000  # Base salary
    
    # Salary multipliers based on skills
    salary_multipliers = {
        'senior': 1.4,
        'lead': 1.35,
        'manager': 1.5,
        'director': 1.7,
        'architect': 1.6,
        'machine learning': 1.4,
        'devops': 1.35,
        'aws': 1.2,
        'kubernetes': 1.25,
        'python': 1.1,
        'java': 1.1,
        'golang': 1.15,
        'rust': 1.2
    }
    
    salary_multiplier = 1.0
    skills = [s.lower() for s in analysis['skills']]
    experience_count = len(analysis['experience'])
    
    # Apply skill-based multipliers
    for skill, multiplier in salary_multipliers.items():
        if skill in skills:
            salary_multiplier *= multiplier
    
    # Apply experience multiplier
    experience_multiplier = 1.0 + (experience_count * 0.15)
    salary_multiplier *= experience_multiplier
    
    estimated_salary = int(base_salary * salary_multiplier)
    salary_range = {
        'low': int(estimated_salary * 0.85),
        'mid': estimated_salary,
        'high': int(estimated_salary * 1.15)
    }
    
    return salary_range

def suggest_career_paths(analysis):
    """Suggest career paths based on resume analysis."""
    skills = set([s.lower() for s in analysis['skills']])
    experience_count = len(analysis['experience'])
    
    career_suggestions = []
    
    # Data Science path
    data_science_skills = {'python', 'r', 'machine learning', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'sql'}
    if len(skills.intersection(data_science_skills)) >= 3:
        career_suggestions.append({
            'path': 'Data Science',
            'relevance': 'High',
            'required_skills': list(data_science_skills - skills),
            'potential_roles': ['Data Scientist', 'ML Engineer', 'Analytics Engineer']
        })
    
    # DevOps path
    devops_skills = {'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'jenkins', 'terraform'}
    if len(skills.intersection(devops_skills)) >= 2:
        career_suggestions.append({
            'path': 'DevOps Engineering',
            'relevance': 'High',
            'required_skills': list(devops_skills - skills),
            'potential_roles': ['DevOps Engineer', 'Cloud Architect', 'Infrastructure Engineer']
        })
    
    # Backend Development path
    backend_skills = {'python', 'java', 'node.js', 'go', 'rust', 'sql', 'rest', 'microservices'}
    if len(skills.intersection(backend_skills)) >= 3:
        career_suggestions.append({
            'path': 'Backend Development',
            'relevance': 'High',
            'required_skills': list(backend_skills - skills),
            'potential_roles': ['Backend Engineer', 'Software Architect', 'Technical Lead']
        })
    
    # Frontend Development path
    frontend_skills = {'javascript', 'react', 'angular', 'vue', 'html', 'css', 'typescript'}
    if len(skills.intersection(frontend_skills)) >= 3:
        career_suggestions.append({
            'path': 'Frontend Development',
            'relevance': 'High',
            'required_skills': list(frontend_skills - skills),
            'potential_roles': ['Frontend Engineer', 'UI/UX Engineer', 'Lead Frontend Developer']
        })
    
    # Full Stack Development path
    fullstack_skills = {'javascript', 'python', 'react', 'node.js', 'sql', 'html', 'css'}
    if len(skills.intersection(fullstack_skills)) >= 4:
        career_suggestions.append({
            'path': 'Full Stack Development',
            'relevance': 'High',
            'required_skills': list(fullstack_skills - skills),
            'potential_roles': ['Full Stack Engineer', 'Software Engineer', 'Senior Developer']
        })
    
    # Management path
    if experience_count >= 3:
        career_suggestions.append({
            'path': 'Technical Management',
            'relevance': 'Medium' if experience_count >= 3 else 'Low',
            'required_skills': ['Leadership', 'Communication', 'Project Management'],
            'potential_roles': ['Engineering Manager', 'Team Lead', 'Director of Engineering']
        })
    
    return career_suggestions

# ==================== API ENDPOINTS ====================

@app.route('/')
def home():
    """Home page."""
    return jsonify({
        'message': 'Resume Analyser API',
        'version': '2.0',
        'endpoints': {
            'analyze': '/api/analyze',
            'compare': '/api/compare',
            'salary': '/api/salary',
            'career': '/api/career-paths',
            'readability': '/api/readability',
            'export': '/api/export'
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze a single resume."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save and process file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Extract text based on file type
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.txt'):
            text = extract_text_from_txt(filepath)
        else:
            return jsonify({'error': 'Unsupported file format. Use PDF or TXT'}), 400
        
        if not text:
            return jsonify({'error': 'Could not extract text from file'}), 400
        
        analysis = analyze_resume(text)
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'analysis': analysis
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/compare', methods=['POST'])
def compare():
    """Compare two resumes."""
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({'error': 'Both file1 and file2 are required'}), 400
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': 'Both files must be selected'}), 400
    
    try:
        # Process first file
        filename1 = secure_filename(file1.filename)
        filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
        file1.save(filepath1)
        
        if filename1.endswith('.pdf'):
            text1 = extract_text_from_pdf(filepath1)
        elif filename1.endswith('.txt'):
            text1 = extract_text_from_txt(filepath1)
        else:
            return jsonify({'error': 'Unsupported format for file1'}), 400
        
        # Process second file
        filename2 = secure_filename(file2.filename)
        filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
        file2.save(filepath2)
        
        if filename2.endswith('.pdf'):
            text2 = extract_text_from_pdf(filepath2)
        elif filename2.endswith('.txt'):
            text2 = extract_text_from_txt(filepath2)
        else:
            return jsonify({'error': 'Unsupported format for file2'}), 400
        
        comparison = compare_resumes(text1, text2)
        
        return jsonify({
            'status': 'success',
            'file1': filename1,
            'file2': filename2,
            'comparison': comparison
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        for filepath in [filepath1, filepath2]:
            if os.path.exists(filepath):
                os.remove(filepath)

@app.route('/api/salary', methods=['POST'])
def salary():
    """Estimate salary based on resume."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.txt'):
            text = extract_text_from_txt(filepath)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        analysis = analyze_resume(text)
        salary_estimate = estimate_salary(analysis)
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'salary_estimate': salary_estimate,
            'currency': 'USD',
            'basis': 'annual'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/career-paths', methods=['POST'])
def career_paths():
    """Suggest career paths based on resume."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.txt'):
            text = extract_text_from_txt(filepath)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        analysis = analyze_resume(text)
        suggestions = suggest_career_paths(analysis)
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'current_skills': analysis['skills'],
            'career_path_suggestions': suggestions
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/readability', methods=['POST'])
def readability():
    """Analyze resume readability."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.txt'):
            text = extract_text_from_txt(filepath)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        readability_score = calculate_readability(text)
        
        recommendations = []
        if readability_score.get('grade_level', 0) > 14:
            recommendations.append('Simplify complex language for better readability')
        if readability_score.get('avg_words_per_sentence', 0) > 20:
            recommendations.append('Use shorter sentences')
        if readability_score.get('word_count', 0) > 1000:
            recommendations.append('Consider condensing the resume')
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'readability_metrics': readability_score,
            'recommendations': recommendations
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/export', methods=['POST'])
def export_analysis():
    """Export resume analysis as PDF report."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.txt'):
            text = extract_text_from_txt(filepath)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        analysis = analyze_resume(text)
        salary_estimate = estimate_salary(analysis)
        career_suggestions = suggest_career_paths(analysis)
        
        # Generate PDF report
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30
        )
        elements.append(Paragraph('Resume Analysis Report', title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Analysis timestamp
        elements.append(Paragraph(f"Generated: {analysis['analysis_timestamp']}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Contact Information
        elements.append(Paragraph('Contact Information', styles['Heading2']))
        contact = analysis['contact_info']
        contact_text = f"Email: {contact['email'] or 'Not found'}<br/>Phone: {contact['phone'] or 'Not found'}"
        elements.append(Paragraph(contact_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Skills
        elements.append(Paragraph('Skills', styles['Heading2']))
        skills_text = ', '.join(analysis['skills']) or 'No skills identified'
        elements.append(Paragraph(skills_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Salary Estimate
        elements.append(Paragraph('Estimated Salary Range', styles['Heading2']))
        salary_text = f"Low: ${salary_estimate['low']:,} | Mid: ${salary_estimate['mid']:,} | High: ${salary_estimate['high']:,}"
        elements.append(Paragraph(salary_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Readability
        elements.append(Paragraph('Readability Metrics', styles['Heading2']))
        readability = analysis['readability']
        readability_text = f"Grade Level: {readability.get('grade_level', 'N/A')} | Complexity: {readability.get('complexity', 'N/A')}<br/>Word Count: {readability.get('word_count', 'N/A')} | Avg Words/Sentence: {readability.get('avg_words_per_sentence', 'N/A')}"
        elements.append(Paragraph(readability_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Career Paths
        elements.append(Paragraph('Career Path Suggestions', styles['Heading2']))
        for suggestion in career_suggestions:
            career_text = f"<b>{suggestion['path']}</b> ({suggestion['relevance']})<br/>Potential Roles: {', '.join(suggestion['potential_roles'])}"
            elements.append(Paragraph(career_text, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(elements)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='resume_analysis_report.pdf'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error',
        'status': 500
    }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
