from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from pydantic import BaseModel
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize LLM and embeddings
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# Define the state schema
class SharedInput(BaseModel):
    input: str
    course_id: str = "default"
    file_path: Optional[str] = None
    extracted_info: str = None
    questions: str = None
    prompts: str = None
    evaluation: str = None
    relevant_context: str = None
    document_chunks: List[str] = []

class DocumentProcessor:
    """Handle document loading and processing using LangChain"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def process_file(self, file_path: Path) -> List[str]:
        """Process uploaded file and return text chunks"""
        try:
            # Load document based on file type
            if file_path.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif file_path.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path))
            elif file_path.suffix.lower() == '.txt':
                loader = TextLoader(str(file_path))
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
            
            # Load and split documents
            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)
            
            # Extract text content from chunks
            text_chunks = [chunk.page_content for chunk in chunks]
            
            logger.info(f"Successfully processed {file_path}: {len(text_chunks)} chunks created")
            return text_chunks
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

class SimpleCourseLibrary:
    """Simplified course library without vector store dependencies"""
    
    def __init__(self):
        self.course_libraries = {}
        self.library_path = Path("course_libraries")
        self.library_path.mkdir(exist_ok=True)
    
    def add_course_document(self, course_id: str, title: str, content: str, 
                          author: str = "", doc_type: str = "text"):
        """Add a document to course library"""
        if course_id not in self.course_libraries:
            self.course_libraries[course_id] = []
        
        document = {
            "id": len(self.course_libraries[course_id]) + 1,
            "title": title,
            "content": content,
            "author": author,
            "type": doc_type
        }
        
        self.course_libraries[course_id].append(document)
        self._save_course_library(course_id)
        return document
    
    def add_document_chunks(self, course_id: str, chunks: List[str], title: str = "Uploaded Document"):
        """Add document chunks to course library"""
        for i, chunk in enumerate(chunks):
            self.add_course_document(
                course_id=course_id,
                title=f"{title} - Part {i+1}",
                content=chunk,
                author="Uploaded Content",
                doc_type="uploaded_file"
            )
    
    def _save_course_library(self, course_id: str):
        """Save course library to file"""
        file_path = self.library_path / f"{course_id}.json"
        with open(file_path, 'w') as f:
            json.dump(self.course_libraries[course_id], f, indent=2)
    
    def load_course_library(self, course_id: str):
        """Load course library from file"""
        file_path = self.library_path / f"{course_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                self.course_libraries[course_id] = json.load(f)
        return self.course_libraries.get(course_id, [])
    
    def search_documents(self, course_id: str, query: str, max_results: int = 5) -> List[Dict]:
        """Simple text-based search without vector embeddings"""
        documents = self.load_course_library(course_id)
        query_words = set(query.lower().split())
        
        scored_docs = []
        for doc in documents:
            doc_text = f"{doc['title']} {doc['content']}".lower()
            doc_words = set(doc_text.split())
            
            overlap = len(query_words.intersection(doc_words))
            if overlap > 0:
                scored_docs.append((overlap, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:max_results]]

# Initialize components
course_library = SimpleCourseLibrary()
doc_processor = DocumentProcessor()

# Agent A: Extract Information and Find Relevant Context
class ExtractorAgent(Runnable):
    def invoke(self, state, config=None):
        input_text = state.input
        document_chunks = []
        
        if state.file_path:
            try:
                file_path = Path(state.file_path)
                if file_path.exists():
                    document_chunks = doc_processor.process_file(file_path)
                    course_library.add_document_chunks(
                        state.course_id, 
                        document_chunks, 
                        f"Uploaded: {file_path.name}"
                    )
                    input_text = " ".join(document_chunks[:3])
                    logger.info(f"Processed uploaded file: {len(document_chunks)} chunks")
                else:
                    logger.warning(f"File not found: {file_path}")
            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}")
        
        extract_prompt = f"""
        Analyze the following text and extract:
        1. Main ideas and key concepts
        2. Important keywords and terminology
        3. Core themes and topics
        4. Educational objectives that could be addressed
        
        Text to analyze:
        {input_text[:2000]}...  
        """
        
        extract_response = llm.invoke([HumanMessage(content=extract_prompt)])
        extracted_info = extract_response.content
        
        relevant_context = ""
        try:
            relevant_docs = course_library.search_documents(state.course_id, extracted_info)
            
            if relevant_docs:
                context_pieces = []
                for doc in relevant_docs:
                    context_pieces.append(f"Title: {doc['title']}\nAuthor: {doc['author']}\nContent: {doc['content'][:300]}...")
                
                relevant_context = "\n\n---\n\n".join(context_pieces)
                logger.info(f"Found {len(relevant_docs)} relevant documents")
            else:
                relevant_context = "No relevant course materials found."
                
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            relevant_context = "Error retrieving course materials."
        
        return {
            "extracted_info": extracted_info,
            "relevant_context": relevant_context,
            "document_chunks": document_chunks,
            "input": input_text
        }

# Agent B: Generate Questions and Teacher Prompts
class ScaffoldPromptAgent(Runnable):
    def invoke(self, state, config=None):
        context_section = ""
        if state.relevant_context and state.relevant_context != "No relevant course materials found.":
            context_section = f"\n\nRelevant Course Materials:\n{state.relevant_context}\n"
        
        prompt = f"""
        Based on the following information and any relevant course materials, create Reading Apprenticeship (RA) questions and teacher prompts.

        TASK:
        1. Generate 4 comprehension questions aligned with the Reading Apprenticeship (RA) framework:
           - Social: Promotes discussion, collaboration, or peer interaction
           - Personal: Invites self-reflection, personal connection, or prior experience
           - Cognitive: Encourages metacognition, reading strategies, or thinking about thinking
           - Knowledge-Building: Deepens understanding of concepts, content knowledge, or subject matter

        2. Create a concise teacher prompt (1–2 sentences) for each question to guide facilitation.

        FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
        Questions:
        1. [Social question]
        2. [Personal question] 
        3. [Cognitive question]
        4. [Knowledge-Building question]

        Prompts:
        1. [Teacher prompt for question 1]
        2. [Teacher prompt for question 2]
        3. [Teacher prompt for question 3]
        4. [Teacher prompt for question 4]

        PRIMARY INFORMATION:
        {state.extracted_info}
        {context_section}
        
        Make the questions specific to the content while maintaining the RA framework structure.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        output = response.content
        
        try:
            if "Prompts:" in output:
                questions_part = output.split("Prompts:")[0].replace("Questions:", "").strip()
                prompts_part = output.split("Prompts:")[1].strip()
            else:
                questions_part = output
                prompts_part = "Prompts not properly formatted."
                
            logger.info("Successfully generated questions and prompts")
        except Exception as e:
            logger.error(f"Error parsing output: {str(e)}")
            questions_part = output
            prompts_part = "Error parsing prompts."
        
        return {
            "questions": questions_part,
            "prompts": prompts_part
        }

# Agent C: Quality Check and Evaluation
class QualityAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = f"""
        Evaluate the following Reading Apprenticeship questions and teacher prompts for quality and alignment.

        EVALUATION CRITERIA:
        For each question, assess:
        1. RA Framework Alignment: Which dimension (Social, Personal, Cognitive, Knowledge-Building) and how well it fits
        2. Clarity: Is the question clear and understandable?
        3. Educational Value: Does it promote meaningful learning?
        4. Content Relevance: Does it connect well to the reading material?

        For each teacher prompt, evaluate:
        1. Facilitation Guidance: How well does it guide teacher action?
        2. Student Engagement: Will it promote active participation?
        3. Clarity: Is it actionable and specific?

        QUESTIONS:
        {state.questions}

        TEACHER PROMPTS:
        {state.prompts}

        Provide a structured evaluation with:
        - Overall assessment (Excellent/Good/Needs Improvement)
        - Specific strengths
        - Areas for improvement
        - Recommendations for enhancement
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        logger.info("Quality evaluation completed")
        
        return {"evaluation": response.content}

# Create the LangGraph workflow
def create_workflow():
    workflow = StateGraph(SharedInput)
    
    workflow.add_node("extractor", ExtractorAgent())
    workflow.add_node("scaffold_prompt", ScaffoldPromptAgent())
    workflow.add_node("quality", QualityAgent())
    
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "scaffold_prompt")
    workflow.add_edge("scaffold_prompt", "quality")
    workflow.set_finish_point("quality")
    
    return workflow.compile()

# Initialize the workflow
workflow_app = create_workflow()

def setup_example_course():
    """Set up an example course with sample documents"""
    course_id = "reading-apprenticeship-demo"
    
    course_library.add_course_document(
        course_id=course_id,
        title="Reading Apprenticeship Framework Overview",
        content="""
        Reading Apprenticeship is a professional development program that focuses on improving 
        adolescent literacy across subject areas. The framework consists of four dimensions:

        Social Dimension: Creating a safe environment for students to share their reading processes,
        discuss comprehension challenges, and learn from each other's strategies.

        Personal Dimension: Helping students develop reading identities, connect texts to their 
        experiences, and build confidence as readers.

        Cognitive Dimension: Making visible the mental processes involved in reading comprehension,
        including metacognitive strategies and problem-solving approaches.

        Knowledge-Building Dimension: Developing subject-area knowledge and understanding how 
        knowledge shapes reading comprehension in different disciplines.
        """,
        author="WestEd Reading Apprenticeship",
        doc_type="framework_guide"
    )
    
    return course_id

def process_uploaded_file(file_path: str, course_id: str = None, custom_input: str = ""):
    """Process an uploaded file through the RA question generation workflow"""
    
    if not course_id:
        course_id = f"upload_{Path(file_path).stem}"
    
    # Set up course if it doesn't exist
    if course_id not in course_library.course_libraries:
        setup_example_course()
    
    logger.info(f"Processing file: {file_path}")
    logger.info(f"Course ID: {course_id}")
    
    input_state = SharedInput(
        input=custom_input or "Analyze the uploaded document and generate Reading Apprenticeship questions.",
        course_id=course_id,
        file_path=file_path
    )
    
    try:
        result = workflow_app.invoke(input_state)
        logger.info("Workflow completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}")
        return None