from fastapi import FastAPI, File, UploadFile
import pdfplumber
import pandas as pd
import tabula
import pytesseract
import cv2
import io
import pdf2image
from collections import OrderedDict

app = FastAPI()

def extract_tables_with_pdfplumber(pdf_file):
    """Extracts tables from a PDF using pdfplumber."""
    tables = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extracted_table = page.extract_table()
            if extracted_table:
                df = pd.DataFrame(extracted_table[1:], columns=extracted_table[0])
                tables.append(df.to_dict(orient="records"))
    return tables

def extract_tables_with_tabula(pdf_file):
    """Extracts tables from a PDF using Tabula (works best for structured PDFs)."""
    try:
        tables = tabula.read_pdf(pdf_file, pages="all", multiple_tables=True)
        return [df.to_dict(orient="records") for df in tables]
    except:
        return []

def extract_text_with_ocr(pdf_file):
    """Extracts text from scanned PDFs using OCR."""
    images = pdf2image.convert_from_bytes(pdf_file.read())
    extracted_text = []
    for img in images:
        img_cv = cv2.cvtColor(cv2.imread(img.filename), cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(img_cv)
        extracted_text.append(text)
    return "\n".join(extracted_text)

@app.post("/extract-tables/")
async def extract_tables_api(file: UploadFile = File(...)):
    pdf_bytes = io.BytesIO(await file.read())

    # Try structured table extraction first
    extracted_data = extract_tables_with_pdfplumber(pdf_bytes)
    if not extracted_data:
        extracted_data = extract_tables_with_tabula(pdf_bytes)

    # If no structured tables, fall back to OCR extraction
    if not extracted_data:
        extracted_text = extract_text_with_ocr(pdf_bytes)
        return {"error": "No structured tables found. Extracted raw text instead.", "text": extracted_text}

    return {"tables": extracted_data}