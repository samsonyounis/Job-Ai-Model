from fastapi import FastAPI
from pydantic import BaseModel
from job_match import extract_keywords, calculate_similarity

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
