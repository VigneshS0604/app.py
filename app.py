import os
from flask import Flask, render_template, request, redirect, url_for, flash
import re
import pdfplumber
import docx
import spacy

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Used for session management (e.g., flash messages)

# Load the NLP model
nlp = spacy.load("en_core_web_sm")

# Define regular expressions for email, phone number, LinkedIn URL, and education section extraction
email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
phone_regex = r'\b(?:\+?\d{1,3})?[.\-\s]?\(?\d{2,4}\)?[.\-\s]?\d{3}[.\-\s]?\d{4}\b'
linkedin_regex = r'\b(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[A-Za-z0-9_-]+\/?\b'
education_header_regex = r'EDUCATION|ACADEMIC BACKGROUND|QUALIFICATIONS|DEGREE|COURSEWORK|UNIVERSITY'

# Define patterns to detect bullet points or sections with skills
bullet_points_regex = r'[\•\●\-\*\•\▪]\s*(.*)'
skills_header_regex = r'SKILLS|TECHNOLOGIES|TOOLS|EXPERTISE|TECHNICAL SKILLS|PROFICIENCIES|STRENGTHS'

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ''
    return text

# Function to extract text from Word document
def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# Function to extract skills from the text without predefined skills list
def extract_skills(text):
    extracted_skills = set()

    # Split text into lines
    lines = text.split('\n')
    capture_skills = False

    for line in lines:
        # Start capturing skills if we detect a header like "Skills"
        if re.search(skills_header_regex, line, re.IGNORECASE):
            capture_skills = True
            continue

        # Stop capturing when we hit an empty line or a new section like "Education"
        if capture_skills:
            bullet_match = re.match(bullet_points_regex, line.strip())
            if bullet_match:  # Bullet point format for skills
                skills = bullet_match.group(1).split(',')
                extracted_skills.update(skill.strip() for skill in skills)
            elif line.strip() == "" or re.search(education_header_regex, line, re.IGNORECASE):  # End of skills section
                capture_skills = False

    return list(extracted_skills)

# Function to extract education details from the text
def extract_education(text):
    education_section = []
    lines = text.split('\n')
    capture_education = False

    for line in lines:
        # Start capturing education details when we detect a header
        if re.search(education_header_regex, line, re.IGNORECASE):
            capture_education = True
            continue

        if capture_education:
            # Stop capturing when we hit an empty line or new section
            if line.strip() == "" or re.search(skills_header_regex, line, re.IGNORECASE):  # New section or empty line
                capture_education = False
            else:
                education_section.append(line.strip())

    return "\n".join(education_section)

# Function to extract email, phone number, name, LinkedIn, skills, and education from text
def extract_info(text):
    # Extract email using regex
    email = re.findall(email_regex, text)
    email = email[0] if email else None

    # Extract phone number using regex
    phone = re.findall(phone_regex, text)
    phone = phone[0] if phone else None

    # Extract LinkedIn ID using regex
    linkedin = re.findall(linkedin_regex, text)
    linkedin = linkedin[0] if linkedin else None

    # Attempt to extract name using spaCy NER
    doc = nlp(text)
    potential_name = None
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            potential_name = ent.text.strip()
            break

    # Extract skills dynamically from the text
    extracted_skills = extract_skills(text)

    # Extract education details
    education = extract_education(text)

    return {
        'Name': potential_name,
        'Phone': phone,
        'Email': email,
        'LinkedIn': linkedin,
        'Skills': extracted_skills,
        'Education': education
    }

# Function to process the resume and extract the desired information
def process_resume(file_path):
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format")

    extracted_info = extract_info(text)
    return extracted_info

# Route for the index page
@app.route('/')
def index(): 
    return render_template('index.html')

# Route for uploading and processing resume
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        try:
            # Process the uploaded resume
            extracted_info = process_resume(file_path)

            return render_template('result.html', info=extracted_info)
        except Exception as e:
            flash(f'Error processing file: {e}')
            return redirect(url_for('index'))
    else:
        flash('Unsupported file format. Please upload a .pdf or .docx file.')
        return redirect(url_for('index'))

if __name__ == "__main__":
    # Create upload directory if not exists
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    app.run(debug=True)
