import os
import time
import uuid
import openai
from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException
from io import BytesIO
import docx
import io
# import pymupdf as fitz
import pytesseract
from gtts import gTTS, tts
from openai import OpenAI
from pdf2image import convert_from_bytes
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymupdf import pymupdf
from fastapi.responses import StreamingResponse
from scipy.io.wavfile import write as write_wav

app = FastAPI()
load_dotenv()
client = OpenAI()

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
class QueryRequest(BaseModel):
    file_id: str
    question: str

# OpenAI API Key
KEY = os.getenv("OPENAI_API_KEY")

if not KEY:
    raise ValueError("API_KEY is not set in the environment.")
openai_client = openai.OpenAI(api_key=KEY)


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
    You are an expert in scoring candidate against the job description. score the resume below against
    the job description below:


    This is the Resume Text below:
    {text}
    this is the job description
    {desc}

    Just return the overall score in percentage and recommendation.
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
    
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

def synthesize_with_gtts(text, output_dir="generated_audio") -> str:
    """Fallback TTS using Google gTTS and returns saved audio file path."""
    os.makedirs(output_dir, exist_ok=True)
    file_name = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(output_dir, file_name)
    tts = gTTS(text)
    tts.save(file_path)
    return file_path


@app.post("/api/tts/")
def generate_audio(data: dict = Body(...)):
    text = data["text"]

    try:
        # Generate audio using your local TTS model
        wav = tts.tts(text)  # Should return a NumPy array of audio samples
        sample_rate = 22050  # Or whatever your TTS model uses

        # Save to in-memory buffer
        buffer = BytesIO()
        write_wav(buffer, sample_rate, wav)
        buffer.seek(0)

        return StreamingResponse(buffer, media_type="audio/wav", headers={
            "Content-Disposition": "inline; filename=tts_audio.wav"
        })

    except Exception as e:
        print(f"Local TTS failed, falling back to gTTS. Reason: {str(e)}")
        try:
            file_path = synthesize_with_gtts(text)
            return StreamingResponse(open(file_path, "rb"), media_type="audio/wav", headers={
                "Content-Disposition": "inline; filename=gtts_audio.wav"
            })
        except Exception as gtts_error:
            raise HTTPException(status_code=500, detail=f"TTS failed: {str(gtts_error)}")

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
    """Score a candidate against the job desc."""
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
        return {score}
    except Exception as e:
        return {"error": str(e)}

@app.post("/extract/data")
async def extract_data(file: UploadFile = File(...)):
    """Extract tables from the file"""
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

@app.post("/ask/")
def ask_dragon(req: QueryRequest):
    try:
        # Step 1: Create assistant (or reuse an existing assistant)
        assistant = openai_client.beta.assistants.create(
            name="Draconomicon Expert",
            instructions="You answer questions based on the uploaded file.",
            model="gpt-4-turbo",
            tools=[{"type": "file_search"}],
        )

        # Step 2: Create a thread
        thread = openai_client.beta.threads.create()

        # Step 3: Send user message with file reference
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=req.question,
            attachments=[
                {"file_id": req.file_id, "tools": [{"type": "file_search"}]}
            ]
        )

        # Step 4: Run the assistant
        run = openai_client.beta.threads.runs.create(
            assistant_id=assistant.id,
            thread_id=thread.id,
        )

        # Step 5: Wait for the run to complete
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(1)

        if run_status.status != "completed":
            raise HTTPException(status_code=500, detail=f"Run failed: {run_status.status}")

        # Step 6: Fetch the latest message
        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        return {"answer": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
