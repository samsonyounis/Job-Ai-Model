from fastapi import FastAPI, File, UploadFile
import pdfplumber
import docx
import spacy
import io
import re
from typing import Dict

app = FastAPI()
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(file):
    """Extract text from PDF"""
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text

def extract_text_from_docx(file):
    """Extract text from DOCX"""
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_contact_info(text: str) -> Dict:
    """Extract contact details (email, phone, LinkedIn, GitHub)"""
    contact_info = {}

    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    contact_info["Email"] = email_match.group() if email_match else ""

    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}[-.\s]?\d{0,4}", text)
    contact_info["Phone"] = phone_match.group() if phone_match else ""

    linkedin_match = re.search(r"https?://(www\.)?linkedin\.com/in/[A-Za-z0-9-_/]+", text)
    contact_info["LinkedIn"] = linkedin_match.group() if linkedin_match else ""

    github_match = re.search(r"https?://(www\.)?github\.com/[A-Za-z0-9-_/]+", text)
    contact_info["GitHub"] = github_match.group() if github_match else ""

    return contact_info

def parse_resume(text: str) -> Dict:
    """Extract structured data from resume"""
    doc = nlp(text)
    sections = {
        "Contact Information": extract_contact_info(text),
        "Summary": "",
        "Work Experience": [],
        "Education": [],
        "Skills": [],
        "Projects": [],
        "Certifications": []
    }

    # Section Headers and Bullet Pattern
    section_keywords = {
        "Work Experience": ["experience", "employment", "professional history"],
        "Education": ["education", "academic", "university", "college", "degree"],
        "Skills": ["skills", "technologies", "proficiencies"],
        "Projects": ["projects", "portfolio", "case studies"],
        "Certifications": ["certifications", "certificates", "licenses"],
        "Summary": ["summary", "profile", "about"]
    }
    bullet_pattern = re.compile(r"•\s+|\d+\.\s+|- ")  # Detects bullets like •, 1., -

    lines = text.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect section headers
        for section, keywords in section_keywords.items():
            if any(keyword in line.lower() for keyword in keywords):
                current_section = section
                break

        if current_section:
            if bullet_pattern.match(line):
                sections[current_section].append(line)
            else:
                if current_section != "Summary":
                    sections[current_section].append(line)
                else:
                    sections[current_section] += line + " "

    return sections

@app.post("/parse-resume/")
async def parse_resume_api(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1].lower()

    if file_ext == "pdf":
        text = extract_text_from_pdf(io.BytesIO(await file.read()))
    elif file_ext == "docx":
        text = extract_text_from_docx(io.BytesIO(await file.read()))
    else:
        return {"error": "Unsupported file format. Use PDF or DOCX"}

    parsed_data = parse_resume(text)
    return parsed_data
