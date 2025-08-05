# Reading Apprenticeship Question Generator

An AI-powered tool that automatically generates Reading Apprenticeship framework questions and teacher facilitation prompts from uploaded educational documents.

## Overview

This application uses a three-agent LangGraph workflow powered by Google's Gemini AI to analyze educational content and generate questions aligned with the Reading Apprenticeship framework's four dimensions:

- **Social Dimension**: Promotes discussion, collaboration, and peer interaction
- **Personal Dimension**: Invites self-reflection, personal connections, and prior experiences
- **Cognitive Dimension**: Encourages metacognition and reading strategies
- **Knowledge-Building Dimension**: Deepens understanding of concepts and subject matter

## Features

- **Document Upload**: Support for PDF, DOCX, and TXT files
- **AI-Powered Analysis**: Automatic extraction of key concepts and themes
- **Framework-Aligned Questions**: Four questions mapped to RA dimensions
- **Teacher Prompts**: Facilitation guidance for each question
- **Quality Evaluation**: Assessment of generated questions and prompts
- **Modern UI**: Clean, responsive React interface with drag-and-drop upload

## Technology Stack

### Frontend
- **React 18** - User interface
- **Tailwind CSS** - Styling and layout
- **Lucide React** - Icons and visual elements

### Backend
- **FastAPI** - Web API framework
- **LangGraph** - Multi-agent workflow orchestration
- **LangChain** - Document processing and LLM integration
- **Google Gemini AI** - Language model for content analysis
- **PyPDF/python-docx** - Document parsing

## Prerequisites

- **Node.js** (v14 or higher)
- **Python** (v3.8 or higher)
- **Google API Key** for Gemini AI

## Installation

### 1. Clone or Download the Project

```bash
git clone <your-repo-url>
cd ra-question-generator
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend/ra-question-generator

# Install Node.js dependencies
npm install
```

### 4. Environment Configuration

Create a `.env` file in the backend directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

**To get a Google API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create an API key for Gemini
3. Add it to your `.env` file

## Project Structure

```
RA_Inkspire/
├── backend/
│   ├── venv/                 # Virtual environment
│   ├── backend.py           # FastAPI server
│   ├── ra_workflow.py       # LangGraph workflow
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # Environment variables
│   └── course_libraries/    # Generated course data
└── frontend/
    └── ra-question-generator/
        ├── src/
        │   ├── App.js
        │   └── RAQuestionGenerator.js
        ├── public/
        ├── package.json
        └── ...
```

## Required Dependencies

### Backend (`requirements.txt`)
```txt
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
langgraph
langchain-core
langchain-google-genai
langchain-community
python-dotenv
pydantic
pypdf
python-docx
docx2txt
```

### Frontend (`package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "lucide-react": "^0.263.1"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

## Running the Application

### 1. Start the Backend Server

```bash
cd backend
source venv/bin/activate
python backend.py
```

The backend will start on `http://localhost:8000`

### 2. Start the Frontend Development Server

```bash
cd frontend/ra-question-generator
npm start
```

The frontend will open at `http://localhost:3000`

## Usage

1. **Open the application** in your browser at `http://localhost:3000`
2. **Upload a document** by dragging and dropping or clicking to browse (PDF, DOCX, or TXT)
3. **Click "Generate RA Questions"** to process the document
4. **Review the results** including:
   - Document analysis and key concepts
   - Generated Reading Apprenticeship questions
   - Teacher facilitation prompts
   - Quality evaluation and recommendations

## How It Works

### Three-Agent Workflow

1. **Extractor Agent**: Processes uploaded documents, extracts key information, and finds relevant course context
2. **Scaffold Prompt Agent**: Generates Reading Apprenticeship questions and teacher prompts aligned with the four dimensions
3. **Quality Agent**: Evaluates the generated questions for alignment, clarity, and educational value

### Document Processing Pipeline

1. **File Upload**: Documents are temporarily stored and validated
2. **Text Extraction**: Content is extracted using appropriate parsers (PyPDF, python-docx, etc.)
3. **Chunking**: Large documents are split into manageable chunks
4. **AI Analysis**: Gemini AI analyzes content for key concepts and themes
5. **Question Generation**: Framework-specific questions are created
6. **Quality Assurance**: Generated content is evaluated and scored

## API Endpoints

### `POST /process-file`
- **Description**: Process uploaded document and generate RA questions
- **Parameters**: Multipart form data with file upload
- **Response**: JSON with extracted info, questions, prompts, and evaluation

### `GET /health`
- **Description**: Health check endpoint
- **Response**: `{"status": "healthy"}`

## Supported File Formats

- **PDF** (.pdf) - Requires `pypdf` package
- **Word Documents** (.docx) - Requires `python-docx` package  
- **Text Files** (.txt) - Native support
- **File Size Limit**: 10MB maximum

## Reading Apprenticeship Framework

The generated questions align with the four dimensions of Reading Apprenticeship:

### Social Dimension (Blue)
- Encourages peer discussion and collaboration
- Builds classroom community around reading
- Promotes shared inquiry and learning

### Personal Dimension (Green)
- Connects reading to students' lives and experiences
- Develops reading identity and confidence
- Encourages personal reflection and growth

### Cognitive Dimension (Purple)
- Makes thinking processes visible
- Teaches metacognitive strategies
- Develops reading comprehension skills

### Knowledge-Building Dimension (Orange)
- Deepens content understanding
- Connects to subject-area knowledge
- Builds disciplinary thinking skills

## Troubleshooting

### Backend Issues

**ImportError: cannot import name 'process_uploaded_file'**
- Ensure `ra_workflow.py` contains the complete workflow code
- Check that all required functions are defined

**ModuleNotFoundError: No module named 'fastapi'**
- Make sure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

**PDF processing errors**
- Install PDF reader: `pip install pypdf`
- For alternative: `pip install PyPDF2`

### Frontend Issues

**React Error #130**
- Check browser console for detailed errors
- Restart React app: `npm start`
- Clear cache: `rm -rf node_modules/.cache`

**Connection Refused (ERR_CONNECTION_REFUSED)**
- Ensure backend is running on port 8000
- Check CORS configuration
- Test backend health: `curl http://localhost:8000/health`

**Tailwind CSS not working**
- Ensure Tailwind is properly installed: `npm install -D tailwindcss`
- Check `tailwind.config.js` configuration
- Verify `@tailwind` directives in `src/index.css`
