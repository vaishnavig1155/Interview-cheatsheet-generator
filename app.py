from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from PyPDF2 import PdfReader
import requests  
from io import BytesIO
import json
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "Adn!c`96H|U2"  

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
def init_db():
    conn = sqlite3.connect('cheatsheet.db')
    c = conn.cursor()
    
    # Create users table with email
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL)''')
    
    # Create cheatsheets table remains the same
    c.execute('''CREATE TABLE IF NOT EXISTS cheatsheets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 created_at TEXT NOT NULL,
                 job_description TEXT NOT NULL,
                 cheatsheet_data TEXT NOT NULL,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('cheatsheet.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        return User(id=user_data[0], username=user_data[1])
    return None

# Existing PDF extraction function
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(BytesIO(pdf_file.read()))
    return "\n".join(page.extract_text() for page in reader.pages)

# Existing Ollama API function
def generate_with_ollama(resume_text, job_desc):
    prompt = f"""Generate a VALID JSON output with exactly this structure:
    {{
        "swot": {{
            "strengths": ["item1", "item2"],
            "weaknesses": ["item1", "item2"],
            "opportunities": ["item1", "item2"],
            "threats": ["item1", "item2"]
        }},
        "skills": [
            {{"name": "skill1", "match": true}},
            {{"name": "skill2", "match": false}}
        ],
        "questions": [
            {{"question": "Q1", "answer": "A1"}},
            {{"question": "Q2", "answer": "A2"}}
        ]
    }}
    Resume: {resume_text[:2000]}
    Job Description: {job_desc[:2000]}
    Respond ONLY with the JSON object, no commentary or formatting."""
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.3}
            }
        )
        return response.json()["response"]
    except Exception as e:
        print("OLLAMA ERROR:", str(e))
        return None

# Auth routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('cheatsheet.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                     (username, email, hashed_password))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('cheatsheet.db')
        c = conn.cursor()
        c.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1])
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('cheatsheet.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, created_at, job_description 
        FROM cheatsheets 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    """, (current_user.id,))
    
    # Convert tuples to dictionaries for easier template access
    cheatsheets = []
    for row in c.fetchall():
        cheatsheets.append({
            'id': row[0],
            'created_at': row[1],
            'job_description': row[2]
        })
    
    conn.close()
    
    return render_template('dashboard.html', cheatsheets=cheatsheets)
# View saved cheatsheet
@app.route('/cheatsheet/<int:cheatsheet_id>')
@login_required
def view_cheatsheet(cheatsheet_id):
    conn = sqlite3.connect('cheatsheet.db')
    c = conn.cursor()
    c.execute("SELECT cheatsheet_data FROM cheatsheets WHERE id = ? AND user_id = ?", 
             (cheatsheet_id, current_user.id))
    cheatsheet_data = c.fetchone()
    conn.close()
    
    if not cheatsheet_data:
        flash('Cheatsheet not found', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cheatsheet = json.loads(cheatsheet_data[0])
        return render_template('result.html', cheatsheet=cheatsheet)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Modified index route with login requirement
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        file = request.files.get('file')
        job_desc = request.form.get("jobDescription", "").strip()
        
        if not file or not file.filename.endswith('.pdf'):
            flash("Please upload a valid PDF file.", "error")
            return redirect("/")
        
        if not job_desc:
            flash("Job description is required.", "error")
            return redirect("/")
        
        try:
            resume_text = extract_text_from_pdf(file)
            cheatsheet = generate_with_ollama(resume_text, job_desc)
            
            # Save to database
            conn = sqlite3.connect('cheatsheet.db')
            c = conn.cursor()
            c.execute("INSERT INTO cheatsheets (user_id, created_at, job_description, cheatsheet_data) VALUES (?, ?, ?, ?)",
                     (current_user.id, datetime.now().isoformat(), job_desc, cheatsheet))
            conn.commit()
            conn.close()
            
            return render_template("result.html", cheatsheet=json.loads(cheatsheet))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect("/")
    
    return render_template("index.html")

# Modified result route (now handled by view_cheatsheet)