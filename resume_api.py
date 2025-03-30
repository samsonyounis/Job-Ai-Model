import os
import openai
from fastapi import FastAPI, UploadFile, File, Form
from io import BytesIO
import docx
import io
# import pymupdf as fitz
import pytesseract
from pdf2image import convert_from_bytes
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pymupdf import pymupdf

app = FastAPI()
load_dotenv()

origins = [
    "http://localhost:4200",  # Allow requests from frontend running locally
    "https://yourfrontenddomain.com",  # Allow requests from deployed frontend
    "*"  # Allow all domains (use cautiously in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("API_KEY is not set in the environment.")
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# print("Key is: "+OPENAI_API_KEY)


def extract_text_from_pdf(pdf_bytes: BytesIO) -> str:
    """Extract text from a PDF using PyMuPDF and handle scanned PDFs with OCR."""
    doc = pymupdf.open(stream=pdf_bytes.getvalue(), filetype="pdf")

    # Check if PDF is encrypted
    if doc.is_encrypted:
        return "Error: PDF is encrypted."

    text = "\n".join([page.get_text("text") for page in doc])

    # If extracted text is too short, assume it's an image-based (scanned) PDF
    if len(text.strip()) < 10:
        return extract_text_with_ocr(pdf_bytes)

    return text


def extract_text_with_ocr(pdf_bytes: BytesIO) -> str:
    """Extract text from a scanned PDF using OCR."""
    try:
        images = convert_from_bytes(pdf_bytes.getvalue())  # Convert PDF to images
        text = "\n".join([pytesseract.image_to_string(img) for img in images])
        return text.strip()
    except Exception as e:
        return f"Error extracting OCR text: {str(e)}"


def extract_text_from_docx(file):
    """Extract text from DOCX"""
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text


def parse_resume_with_openai(text: str) -> dict:
    """Send resume text to OpenAI and return structured resume data."""
    prompt = f"""
    You are an expert in resume parsing. Extract the following sections from the resume text below and return a structured JSON object:

    - contact_information
    - summary
    - skills
    - experience
    - education
    - certifications
    - hobbies
    - references

    The response must be **only** a valid JSON object, without any additional text, explanations, or formatting. Do **not** include markdown, backticks, or labels like "json".

    Resume Text:
    {text}

    Return only the JSON object.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content

def score_openai(text: str, desc: str) -> dict:
    """Send resume text to OpenAI and return structured resume data."""
    prompt = f"""
    You are an expert in scoring candidate against the jb description. score the resume below against
    the job description below:


    This is the Resume Text below:
    {text}
    this is the job description
    {desc}

    Just return the overall score in percentage and recommendation in string response in structured JSON format.
    The response must be **only** a valid JSON object, without any additional text, explanations, or formatting. Do **not** include markdown, backticks, or labels like "json".
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content

def extract_tables_with_openai(text: str) -> dict:
    """Send resume text to OpenAI and return structured resume data."""
    prompt = f"""
    You are an expert in extracting tables data from pdf. please help me to extract tabular data from
    this pdf text

    This is the pdf text:
    {text}

    just return data the response in this structure form List<Map<String, String>> json. do not add extra explanation;
.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content

def scrape_url_openai(url: str) -> dict:
    """Send resume text to OpenAI and return structured resume data."""
    prompt = f"""
    You are an expert in scraping the website url. please help me to scrape this url and return
    tax fund tax information in structured format. some websites have the information in pdf,csv
    or excel file which have to be downloaded, other websites have the information on tables.
    you may need to click around the page to find the data.

    This is the website url below
    {url}

    just return data the response in this structure form List<Map<String, String>> json. do not add extra explanation;
.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content


@app.post("/parse-resume/")
async def parse_resume(file: UploadFile = File(...)):
    """Extracts resume details and returns structured data."""
    try:
        file_ext = file.filename.split(".")[-1].lower()

        if file_ext == "pdf":
            text = extract_text_from_pdf(io.BytesIO(await file.read()))
        elif file_ext == "docx":
            text = extract_text_from_docx(io.BytesIO(await file.read()))
        else:
            return {"error": "Unsupported file format. Use PDF or DOCX"}
        print("the text is: "+text)
        structured_resume = parse_resume_with_openai(text)
        return {structured_resume}
    except Exception as e:
        return {"error": str(e)}


@app.post("/score/")
async def score_candidate(file: UploadFile = File(...), job_desc: str = Form(...)):
    """Extracts resume details and returns structured data."""
    try:
        file_ext = file.filename.split(".")[-1].lower()

        if file_ext == "pdf":
            resume_text = extract_text_from_pdf(io.BytesIO(await file.read()))
        elif file_ext == "docx":
            resume_text = extract_text_from_docx(io.BytesIO(await file.read()))
        else:
            return {"error": "Unsupported file format. Use PDF or DOCX"}
        print("the text is: "+resume_text)
        score = score_openai(resume_text,job_desc)
        return {"score": score}
    except Exception as e:
        return {"error": str(e)}

@app.post("/extract/data")
async def extract_data(file: UploadFile = File(...)):
    """Extracts resume details and returns structured data."""
    try:
        file_ext = file.filename.split(".")[-1].lower()

        if file_ext == "pdf":
            text = extract_text_from_pdf(io.BytesIO(await file.read()))
        elif file_ext == "docx":
            text = extract_text_from_docx(io.BytesIO(await file.read()))
        else:
            return {"error": "Unsupported file format. Use PDF or DOCX"}
        print("the text is: "+text)
        fund_data = extract_tables_with_openai(text)
        return {"filename": file.filename, "fund_data": fund_data}
    except Exception as e:
        return {"error": str(e)}