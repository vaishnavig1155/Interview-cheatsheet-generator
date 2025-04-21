from flask import Flask, render_template, request, session, redirect, url_for, flash
from PyPDF2 import PdfReader
import requests  
from io import BytesIO
import json
import os

app = Flask(__name__)
app.secret_key = "Adn!c`96H|U2"  

#Function to extract text from a PDF file
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(BytesIO(pdf_file.read()))
    return "\n".join(page.extract_text() for page in reader.pages)

#Function to call the Ollama API
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
                "format": "json",  # Force JSON output
                "stream": False,
                "options": {"temperature": 0.3}  # Reduce randomness
            }
        )
        print("RAW OLLAMA RESPONSE:", response.text)  # Debug line
        return response.json()["response"]
    except Exception as e:
        print("OLLAMA ERROR:", str(e))
        return None

@app.route("/", methods=["GET", "POST"])
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
            session["cheatsheet"] = cheatsheet
            return redirect(url_for("result"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect("/")
    
    return render_template("index.html")

@app.route("/result")
def result():
    cheatsheet = session.get("cheatsheet")
    if not cheatsheet:
        flash("No cheatsheet found", "error")
        return redirect("/")
    
    print("DEBUG - Raw cheatsheet:", cheatsheet) 
    
    try:
        cheatsheet_data = json.loads(cheatsheet)
        print("DEBUG - Parsed cheatsheet:", cheatsheet_data) 
        return render_template("result.html", cheatsheet=cheatsheet_data)
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect("/")