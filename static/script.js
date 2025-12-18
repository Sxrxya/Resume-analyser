/**
 * Resume Analyser - Frontend JavaScript Logic
 * Handles form submission, validation, results display, and alerts
 */

// DOM Elements
const resumeForm = document.getElementById('resumeForm');
const resumeInput = document.getElementById('resumeInput');
const jobDescriptionInput = document.getElementById('jobDescriptionInput');
const submitBtn = document.getElementById('submitBtn');
const resultsContainer = document.getElementById('resultsContainer');
const alertContainer = document.getElementById('alertContainer');
const loadingSpinner = document.getElementById('loadingSpinner');

/**
 * Initialize event listeners
 */
document.addEventListener('DOMContentLoaded', function() {
    if (resumeForm) {
        resumeForm.addEventListener('submit', handleFormSubmission);
    }
    if (resumeInput) {
        resumeInput.addEventListener('change', validateResumeFile);
    }
});

/**
 * Validate resume file
 * @param {Event} event - File input change event
 */
function validateResumeFile(event) {
    const file = event.target.files[0];
    
    if (!file) {
        clearAlert();
        return;
    }

    // Validate file type
    const allowedTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ];

    if (!allowedTypes.includes(file.type)) {
        showAlert(
            'Invalid file type. Please upload a PDF, DOC, DOCX, or TXT file.',
            'error'
        );
        resumeInput.value = '';
        return;
    }

    // Validate file size (max 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
        showAlert(
            'File size exceeds 5MB limit. Please upload a smaller file.',
            'error'
        );
        resumeInput.value = '';
        return;
    }

    // Show success message
    showAlert(`File "${file.name}" selected successfully.`, 'success');
}

/**
 * Handle form submission
 * @param {Event} event - Form submit event
 */
async function handleFormSubmission(event) {
    event.preventDefault();

    // Clear previous alerts and results
    clearAlert();
    clearResults();

    // Validate inputs
    const validation = validateFormInputs();
    if (!validation.isValid) {
        showAlert(validation.message, 'error');
        return;
    }

    // Prepare form data
    const formData = new FormData(resumeForm);

    try {
        // Show loading spinner
        showLoadingSpinner(true);
        submitBtn.disabled = true;

        // Send request to backend
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        // Handle response
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'An error occurred during analysis.');
        }

        const data = await response.json();

        // Display results
        displayResults(data);
        showAlert('Resume analysis completed successfully!', 'success');

    } catch (error) {
        console.error('Error:', error);
        showAlert(
            error.message || 'An unexpected error occurred. Please try again.',
            'error'
        );
    } finally {
        showLoadingSpinner(false);
        submitBtn.disabled = false;
    }
}

/**
 * Validate form inputs
 * @returns {Object} - Validation result with isValid flag and message
 */
function validateFormInputs() {
    // Check if resume file is selected
    if (!resumeInput.files || resumeInput.files.length === 0) {
        return {
            isValid: false,
            message: 'Please upload a resume file.'
        };
    }

    // Check if job description is provided
    const jobDescription = jobDescriptionInput.value.trim();
    if (!jobDescription) {
        return {
            isValid: false,
            message: 'Please enter a job description.'
        };
    }

    // Validate job description length (minimum 10 characters)
    if (jobDescription.length < 10) {
        return {
            isValid: false,
            message: 'Job description must be at least 10 characters long.'
        };
    }

    // Validate job description length (maximum 5000 characters)
    if (jobDescription.length > 5000) {
        return {
            isValid: false,
            message: 'Job description must not exceed 5000 characters.'
        };
    }

    return {
        isValid: true,
        message: ''
    };
}

/**
 * Display analysis results
 * @param {Object} data - Analysis results from backend
 */
function displayResults(data) {
    if (!resultsContainer) return;

    resultsContainer.innerHTML = '';

    // Create results wrapper
    const resultsWrapper = document.createElement('div');
    resultsWrapper.className = 'results-wrapper';

    // Overall Match Score
    if (data.match_score !== undefined) {
        const scoreSection = createScoreCard(data.match_score);
        resultsWrapper.appendChild(scoreSection);
    }

    // Skills Analysis
    if (data.skills_analysis) {
        const skillsSection = createSkillsSection(data.skills_analysis);
        resultsWrapper.appendChild(skillsSection);
    }

    // Experience Analysis
    if (data.experience_analysis) {
        const experienceSection = createExperienceSection(data.experience_analysis);
        resultsWrapper.appendChild(experienceSection);
    }

    // Education Analysis
    if (data.education_analysis) {
        const educationSection = createEducationSection(data.education_analysis);
        resultsWrapper.appendChild(educationSection);
    }

    // Recommendations
    if (data.recommendations && data.recommendations.length > 0) {
        const recommendationsSection = createRecommendationsSection(data.recommendations);
        resultsWrapper.appendChild(recommendationsSection);
    }

    // Missing Keywords
    if (data.missing_keywords && data.missing_keywords.length > 0) {
        const keywordsSection = createMissingKeywordsSection(data.missing_keywords);
        resultsWrapper.appendChild(keywordsSection);
    }

    resultsContainer.appendChild(resultsWrapper);
    resultsContainer.style.display = 'block';

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Create match score card element
 * @param {number} score - Match score (0-100)
 * @returns {HTMLElement} - Score card element
 */
function createScoreCard(score) {
    const scoreSection = document.createElement('div');
    scoreSection.className = 'result-section score-card';

    const scoreColor = getScoreColor(score);
    const scorePercentage = Math.round(score);

    scoreSection.innerHTML = `
        <h2>Match Score</h2>
        <div class="score-circle ${scoreColor}">
            <span class="score-value">${scorePercentage}%</span>
        </div>
        <p class="score-description">${getScoreDescription(score)}</p>
    `;

    return scoreSection;
}

/**
 * Create skills section
 * @param {Object} skillsAnalysis - Skills analysis data
 * @returns {HTMLElement} - Skills section element
 */
function createSkillsSection(skillsAnalysis) {
    const skillsSection = document.createElement('div');
    skillsSection.className = 'result-section';

    let skillsHTML = '<h3>Skills Analysis</h3>';

    if (skillsAnalysis.matched_skills && skillsAnalysis.matched_skills.length > 0) {
        skillsHTML += `
            <div class="skills-category">
                <h4>Matched Skills</h4>
                <div class="skills-list">
                    ${skillsAnalysis.matched_skills.map(skill => 
                        `<span class="skill-badge skill-matched">${escapeHtml(skill)}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    if (skillsAnalysis.missing_skills && skillsAnalysis.missing_skills.length > 0) {
        skillsHTML += `
            <div class="skills-category">
                <h4>Missing Skills</h4>
                <div class="skills-list">
                    ${skillsAnalysis.missing_skills.map(skill => 
                        `<span class="skill-badge skill-missing">${escapeHtml(skill)}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    skillsSection.innerHTML = skillsHTML;
    return skillsSection;
}

/**
 * Create experience section
 * @param {Object} experienceAnalysis - Experience analysis data
 * @returns {HTMLElement} - Experience section element
 */
function createExperienceSection(experienceAnalysis) {
    const experienceSection = document.createElement('div');
    experienceSection.className = 'result-section';

    let experienceHTML = '<h3>Experience Analysis</h3>';

    if (experienceAnalysis.years_required) {
        experienceHTML += `
            <div class="analysis-item">
                <strong>Years Required:</strong>
                <span>${experienceAnalysis.years_required}</span>
            </div>
        `;
    }

    if (experienceAnalysis.years_provided) {
        experienceHTML += `
            <div class="analysis-item">
                <strong>Years Provided:</strong>
                <span>${experienceAnalysis.years_provided}</span>
            </div>
        `;
    }

    if (experienceAnalysis.match) {
        experienceHTML += `
            <div class="analysis-item">
                <strong>Experience Match:</strong>
                <span class="badge ${experienceAnalysis.match ? 'badge-success' : 'badge-warning'}">
                    ${experienceAnalysis.match ? 'Meets Requirements' : 'Below Requirements'}
                </span>
            </div>
        `;
    }

    if (experienceAnalysis.feedback) {
        experienceHTML += `
            <p class="feedback">${escapeHtml(experienceAnalysis.feedback)}</p>
        `;
    }

    experienceSection.innerHTML = experienceHTML;
    return experienceSection;
}

/**
 * Create education section
 * @param {Object} educationAnalysis - Education analysis data
 * @returns {HTMLElement} - Education section element
 */
function createEducationSection(educationAnalysis) {
    const educationSection = document.createElement('div');
    educationSection.className = 'result-section';

    let educationHTML = '<h3>Education Analysis</h3>';

    if (educationAnalysis.required) {
        educationHTML += `
            <div class="analysis-item">
                <strong>Required Education:</strong>
                <span>${escapeHtml(educationAnalysis.required)}</span>
            </div>
        `;
    }

    if (educationAnalysis.provided) {
        educationHTML += `
            <div class="analysis-item">
                <strong>Your Education:</strong>
                <span>${escapeHtml(educationAnalysis.provided)}</span>
            </div>
        `;
    }

    if (educationAnalysis.match !== undefined) {
        educationHTML += `
            <div class="analysis-item">
                <strong>Education Match:</strong>
                <span class="badge ${educationAnalysis.match ? 'badge-success' : 'badge-warning'}">
                    ${educationAnalysis.match ? 'Meets Requirements' : 'Below Requirements'}
                </span>
            </div>
        `;
    }

    if (educationAnalysis.feedback) {
        educationHTML += `
            <p class="feedback">${escapeHtml(educationAnalysis.feedback)}</p>
        `;
    }

    educationSection.innerHTML = educationHTML;
    return educationSection;
}

/**
 * Create recommendations section
 * @param {Array} recommendations - Array of recommendations
 * @returns {HTMLElement} - Recommendations section element
 */
function createRecommendationsSection(recommendations) {
    const recommendationsSection = document.createElement('div');
    recommendationsSection.className = 'result-section';

    let recommendationsHTML = '<h3>Recommendations</h3><ul class="recommendations-list">';

    recommendations.forEach(recommendation => {
        recommendationsHTML += `<li>${escapeHtml(recommendation)}</li>`;
    });

    recommendationsHTML += '</ul>';
    recommendationsSection.innerHTML = recommendationsHTML;

    return recommendationsSection;
}

/**
 * Create missing keywords section
 * @param {Array} keywords - Array of missing keywords
 * @returns {HTMLElement} - Missing keywords section element
 */
function createMissingKeywordsSection(keywords) {
    const keywordsSection = document.createElement('div');
    keywordsSection.className = 'result-section';

    let keywordsHTML = '<h3>Keywords to Add</h3>';
    keywordsHTML += '<p>Consider adding these keywords to your resume:</p>';
    keywordsHTML += '<div class="keywords-list">';

    keywords.forEach(keyword => {
        keywordsHTML += `<span class="keyword-badge">${escapeHtml(keyword)}</span>`;
    });

    keywordsHTML += '</div>';
    keywordsSection.innerHTML = keywordsHTML;

    return keywordsSection;
}

/**
 * Show alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type ('success', 'error', 'warning', 'info')
 */
function showAlert(message, type = 'info') {
    if (!alertContainer) return;

    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type}`;
    alertElement.role = 'alert';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'alert-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', function() {
        alertElement.remove();
    });

    alertElement.innerHTML = `
        <div class="alert-content">
            <span class="alert-message">${escapeHtml(message)}</span>
        </div>
    `;
    alertElement.appendChild(closeBtn);

    alertContainer.appendChild(alertElement);

    // Auto-dismiss success alerts after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (alertElement.parentElement) {
                alertElement.remove();
            }
        }, 5000);
    }
}

/**
 * Clear all alerts
 */
function clearAlert() {
    if (!alertContainer) return;
    alertContainer.innerHTML = '';
}

/**
 * Clear all results
 */
function clearResults() {
    if (!resultsContainer) return;
    resultsContainer.innerHTML = '';
    resultsContainer.style.display = 'none';
}

/**
 * Show/hide loading spinner
 * @param {boolean} show - Whether to show the spinner
 */
function showLoadingSpinner(show) {
    if (!loadingSpinner) return;
    loadingSpinner.style.display = show ? 'block' : 'none';
}

/**
 * Get color class based on score
 * @param {number} score - Match score (0-100)
 * @returns {string} - Color class name
 */
function getScoreColor(score) {
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-fair';
    return 'score-poor';
}

/**
 * Get score description
 * @param {number} score - Match score (0-100)
 * @returns {string} - Description text
 */
function getScoreDescription(score) {
    if (score >= 80) return 'Excellent match! Your resume is highly aligned with this job.';
    if (score >= 60) return 'Good match. Your resume aligns well with the job requirements.';
    if (score >= 40) return 'Fair match. Consider improving your resume for better alignment.';
    return 'Needs improvement. Review recommendations below to strengthen your resume.';
}

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Export functions for external use if needed
 */
window.ResumeAnalyser = {
    validateResumeFile,
    handleFormSubmission,
    validateFormInputs,
    showAlert,
    clearAlert,
    clearResults,
    escapeHtml
};
