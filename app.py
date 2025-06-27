from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from models import db, User, Report

import os
import pdfkit
import uuid
from utils import extract_text_from_pdf, calculate_similarity, extract_skill_match, score_resume_sections

# App setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Email setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'  # Use Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'
mail = Mail(app)

# PDF generator config
config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

# Init
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    match_score = None
    matched_skills = []
    missing_skills = []
    suggestions = []
    section_scores = {}

    if request.method == 'POST':
        jd_text = request.form['job_description']
        resume_file = request.files['resume']

        if resume_file:
            filename = str(uuid.uuid4()) + '.pdf'
            resume_path = os.path.join(UPLOAD_FOLDER, filename)
            resume_file.save(resume_path)

            resume_text = extract_text_from_pdf(resume_path)

            match_score = calculate_similarity(resume_text, jd_text)
            matched_skills, missing_skills, suggestions = extract_skill_match(resume_text, jd_text)
            section_scores = score_resume_sections(resume_text, jd_text)

            # Save in session for PDF/email
            session['resume_path'] = resume_path
            session['jd_text'] = jd_text
            session['match_score'] = match_score
            session['matched_skills'] = matched_skills
            session['missing_skills'] = missing_skills
            session['suggestions'] = suggestions
            session['section_scores'] = section_scores

            # Save to DB
            report = Report(user_id=current_user.id,
                            filename=filename,
                            match_score=match_score)
            db.session.add(report)
            db.session.commit()

    return render_template('index.html',
                        match_score=match_score,
                        matched_skills=matched_skills,
                        missing_skills=missing_skills,
                        suggestions=suggestions,
                        section_scores=section_scores)

# Download report as PDF
@app.route('/download-report')
@login_required
def download_report():
    match_score = session.get('match_score')
    matched_skills = session.get('matched_skills', [])
    missing_skills = session.get('missing_skills', [])
    suggestions = session.get('suggestions', [])
    section_scores = session.get('section_scores', {})

    if match_score is None:
        return "No data available. Please analyze a resume first."

    html = render_template('report.html',
                        match_score=match_score,
                        matched_skills=matched_skills,
                        missing_skills=missing_skills,
                        suggestions=suggestions,
                        section_scores=section_scores)

    try:
        pdf = pdfkit.from_string(html, False, configuration=config, options={'enable-local-file-access': None})
    except Exception as e:
        return f"PDF generation failed: {e}"

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=resume_report.pdf'
    return response

# Email report
@app.route('/email-report')
@login_required
def email_report():
    match_score = session.get('match_score')
    matched_skills = session.get('matched_skills', [])
    missing_skills = session.get('missing_skills', [])
    suggestions = session.get('suggestions', [])
    section_scores = session.get('section_scores', {})

    html = render_template('report.html',
                        match_score=match_score,
                        matched_skills=matched_skills,
                        missing_skills=missing_skills,
                        suggestions=suggestions,
                        section_scores=section_scores)

    try:
        pdf = pdfkit.from_string(html, False, configuration=config, options={'enable-local-file-access': None})
        msg = Message("Your Resume Report", recipients=[current_user.email])
        msg.body = "Attached is your resume analysis report."
        msg.attach("Resume_Report.pdf", "application/pdf", pdf)
        mail.send(msg)
        flash("✅ Report emailed successfully!", "success")
    except Exception as e:
        flash(f"❌ Failed to send email: {str(e)}", "danger")

    return redirect(url_for('index'))

# Report history
@app.route('/my-reports')
@login_required
def my_reports():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('my_reports.html', reports=reports)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Try logging in.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
