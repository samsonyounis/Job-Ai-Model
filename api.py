import io

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from job_match import extract_keywords, calculate_similarity
from resume_api import extract_text_from_pdf, extract_text_from_docx, extract_tables_with_openai, score_openai, \
    parse_resume_with_openai

app = FastAPI()

class JobMatchRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/match")
def match_resume(request: JobMatchRequest):
    resume_keywords = extract_keywords(request.resume_text)
    job_keywords = extract_keywords(request.job_description)
    match_score = calculate_similarity(" ".join(resume_keywords), " ".join(job_keywords))
    return {"match_score": match_score}



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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
