# utils.py

import re
import spacy
from pdfminer.high_level import extract_text
import numpy as np

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
    resume_keywords = extract_keywords(resume_text)
    jd_keywords = extract_keywords(jd_text)

    resume_vec = vectorize(resume_keywords, jd_keywords)
    jd_vec = vectorize(jd_keywords, jd_keywords)

    if np.linalg.norm(resume_vec) == 0 or np.linalg.norm(jd_vec) == 0:
        return 0.0

    similarity = np.dot(resume_vec, jd_vec) / (np.linalg.norm(resume_vec) * np.linalg.norm(jd_vec))
    return round(similarity * 100, 2)

def vectorize(tokens, vocabulary):
    vec = np.zeros(len(vocabulary))
    token_freq = {token: tokens.count(token) for token in tokens}
    vocab_index = {word: i for i, word in enumerate(vocabulary)}
    for token, freq in token_freq.items():
        if token in vocab_index:
            vec[vocab_index[token]] = freq
    return vec

def extract_skill_match(resume_text, jd_text):
    resume_skills = set(extract_keywords(resume_text))
    jd_skills = set(extract_keywords(jd_text))

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)

    suggestions = [f"Consider adding more detail about: {skill}" for skill in missing[:5]]

    return matched, missing, suggestions
