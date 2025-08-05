from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
import uvicorn

# Import your existing workflow - UPDATED LINE
from ra_workflow import process_uploaded_file

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-file")
async def process_file_endpoint(file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Validate file size (10MB limit)
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Create temporary file
    temp_dir = tempfile.mkdtemp()
    temp_file_path = Path(temp_dir) / file.filename
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process file using your existing workflow
        result = process_uploaded_file(
            file_path=str(temp_file_path),
            course_id=f"upload_{Path(file.filename).stem}"
        )
        
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to process file")
        
        # Return results in expected format
        return {
            "extracted_info": result.get("extracted_info", ""),
            "relevant_context": result.get("relevant_context", ""),
            "questions": result.get("questions", ""),
            "prompts": result.get("prompts", ""),
            "evaluation": result.get("evaluation", "")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path.exists():
            temp_file_path.unlink()
        os.rmdir(temp_dir)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)