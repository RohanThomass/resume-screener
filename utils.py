# utils.py


import fitz
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pdfminer.high_level import extract_text
import spacy
try:
    nlp = spacy.load("en_core_web_sm")
except:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")




def extract_text_from_pdf(pdf_path):
    try:
        text = extract_text(pdf_path)
        return text
    except Exception as e:
        return ""
    
def score_resume_sections(resume_text, jd_text):
    jd_text = jd_text.lower()
    section_scores = {}

    sections = {
        'Education': r'(?i)(education|academic background)',
        'Experience': r'(?i)(experience|employment history|work experience)',
        'Projects': r'(?i)(projects|personal projects|key projects)',
        'Skills': r'(?i)(skills|technical skills)',
        'Certifications': r'(?i)(certifications|courses|licenses)',
    }

    for section, pattern in sections.items():
        if re.search(pattern, resume_text):
            section_scores[section] = 1
        else:
            section_scores[section] = 0

    return section_scores


def extract_keywords(text):
    doc = nlp(text)
    return [token.text.lower() for token in doc if token.is_alpha and not token.is_stop]

def calculate_similarity(resume_text, jd_text):
    resume_keywords = " ".join(extract_keywords(resume_text))
    jd_keywords = " ".join(extract_keywords(jd_text))

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_keywords, jd_keywords])
    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return round(score * 100, 2)

def extract_skill_match(resume_text, jd_text):
    resume_skills = set(extract_keywords(resume_text))
    jd_skills = set(extract_keywords(jd_text))

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)

    suggestions = [f"Consider adding more detail about: {skill}" for skill in missing[:5]]

    return matched, missing, suggestions
