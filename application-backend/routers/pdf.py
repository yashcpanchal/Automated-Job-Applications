from fastapi import APIRouter, HTTPException, File, UploadFile
import io
from services.pdf_processing.read_pdf import convert_pdf_to_text
from pydantic import BaseModel
import os
import magic


ALLOWED_TYPES = {
    'application/pdf': 'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 10MB

async def validate_file(file: UploadFile):
    """
    Validate the uploaded file based on length of file and type
    """
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size over 5 MB"
        )
    
    content = await file.read(1024)
    file.file.seek(0)
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type"
        )
    return mime_type

router = APIRouter(
    prefix="/pdf",
    tags=["PDF Processing"]
)

class PDFContent(BaseModel):
    filename: str
    content: str

# This is a POST endpoint to upload and process a PDF file
@router.post("/upload-and-extract", response_model=PDFContent)

async def process_pdf(file: UploadFile = File(...)):
    """
    Upload and extract text from PDF file.
    """
    await validate_file(file)
    # Try to read the file content using file.read()
    try:
        pdf_content = await file.read()
        extracted_text = convert_pdf_to_text(pdf_content)
        if not extracted_text:
            raise HTTPException(status_code=500, detail="Could not extract text from PDF")
        
        return PDFContent(filename=file.filename, content=extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
