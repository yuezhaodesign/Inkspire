from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from pydantic import BaseModel
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import re

# Setup loggin
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
    extracted_info: str = None
    questions: str = None
    prompts: str = None
    evaluation: str = None
    relevant_context: str = None

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
    
    def search_documents(self, course_id: str, query: str, max_results: int = 3) -> List[Dict]:
        """Simple text-based search without vector embeddings"""
        documents = self.load_course_library(course_id)
        query_words = set(query.lower().split())
        
        scored_docs = []
        for doc in documents:
            # Simple scoring based on keyword matches
            doc_text = f"{doc['title']} {doc['content']}".lower()
            doc_words = set(doc_text.split())
            
            # Calculate overlap score
            overlap = len(query_words.intersection(doc_words))
            if overlap > 0:
                scored_docs.append((overlap, doc))
        
        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:max_results]]

# Initialize course library
course_library = SimpleCourseLibrary()

# Agent A: Extract Information and Find Relevant Context
class ExtractorAgent(Runnable):
    def invoke(self, state, config=None):
        # Extract main ideas
        extract_prompt = f"Extract the main ideas and keywords from this text:\n\n{state.input}"
        extract_response = llm.invoke([HumanMessage(content=extract_prompt)])
        extracted_info = extract_response.content
        
        # Search for relevant context using simple text matching
        relevant_context = ""
        try:
            relevant_docs = course_library.search_documents(state.course_id, extracted_info)
            
            if relevant_docs:
                context_pieces = []
                for doc in relevant_docs:
                    context_pieces.append(f"Title: {doc['title']}\nAuthor: {doc['author']}\nContent: {doc['content'][:500]}...")
                
                relevant_context = "\n\n---\n\n".join(context_pieces)
            else:
                relevant_context = "No relevant course materials found."
                
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            relevant_context = "Error retrieving course materials."
        
        return {
            "extracted_info": extracted_info,
            "relevant_context": relevant_context
        }

# Agent B: Generate Questions and Teacher Prompts
class ScaffoldPromptAgent(Runnable):
    def invoke(self, state, config=None):
        context_section = ""
        if state.relevant_context and state.relevant_context != "No relevant course materials found.":
            context_section = f"\n\nRelevant Course Materials:\n{state.relevant_context}\n"
        
        prompt = (
            "Based on the following information and any relevant course materials, create:\n\n"
            "1. Generate 4 comprehension questions aligned with the Reading Apprenticeship (RA) framework:\n"
            "   - Social: Promotes discussion or collaborative thinking\n"
            "   - Personal: Invites self-reflection or personal connection\n"
            "   - Cognitive: Encourages metacognition or strategy use\n"
            "   - Knowledge-Building: Deepens understanding of concepts\n\n"
            "2. Create a short teacher prompt (1–2 sentences) for each question to guide facilitation.\n\n"
            "Format your response exactly as follows:\n"
            "Questions:\n"
            "1. [Social question]\n"
            "2. [Personal question]\n"
            "3. [Cognitive question]\n"
            "4. [Knowledge-Building question]\n\n"
            "Prompts:\n"
            "1. [Teacher prompt for question 1]\n"
            "2. [Teacher prompt for question 2]\n"
            "3. [Teacher prompt for question 3]\n"
            "4. [Teacher prompt for question 4]\n\n"
            f"Primary Information:\n{state.extracted_info}\n"
            f"{context_section}"
        )
        
        response = llm.invoke([HumanMessage(content=prompt)])
        output = response.content
        
        try:
            # Split output into questions and prompts
            if "Prompts:" in output:
                questions_part = output.split("Prompts:")[0].replace("Questions:", "").strip()
                prompts_part = output.split("Prompts:")[1].strip()
            else:
                questions_part = output
                prompts_part = "Prompts not properly formatted."
        except Exception as e:
            logger.error(f"Error parsing output: {str(e)}")
            questions_part = output
            prompts_part = "Error parsing prompts."
        
        return {
            "questions": questions_part,
            "prompts": prompts_part
        }

# Agent C: Quality Check
class QualityAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = (
            "Evaluate the following Reading Apprenticeship questions and teacher prompts:\n\n"
            "For each question, provide:\n"
            "- Which RA dimension it aligns with (Social, Personal, Cognitive, or Knowledge-Building)\n"
            "- A brief justification (1-2 sentences)\n"
            "- Assessment of clarity and educational value\n\n"
            "For each teacher prompt, evaluate:\n"
            "- How well it guides teacher facilitation\n"
            "- Whether it promotes meaningful student engagement\n\n"
            f"Questions:\n{state.questions}\n\n"
            f"Prompts:\n{state.prompts}\n\n"
            "Provide a structured evaluation with specific feedback for improvement."
        )
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"evaluation": response.content}

# Create the LangGraph workflow
def create_workflow():
    workflow = StateGraph(SharedInput)
    
    # Add nodes (agents)
    workflow.add_node("extractor", ExtractorAgent())
    workflow.add_node("scaffold_prompt", ScaffoldPromptAgent())
    workflow.add_node("quality", QualityAgent())
    
    # Define graph edges
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "scaffold_prompt")
    workflow.add_edge("scaffold_prompt", "quality")
    workflow.set_finish_point("quality")
    
    # Compile the graph
    return workflow.compile()

# Initialize the workflow
workflow_app = create_workflow()

def setup_example_course():
    """Set up an example course with sample documents"""
    course_id = "biology-101"
    
    # Add sample documents
    course_library.add_course_document(
        course_id=course_id,
        title="Introduction to Photosynthesis",
        content="""
        Photosynthesis is the process by which plants, algae, and certain bacteria convert light energy, 
        usually from the sun, into chemical energy stored in glucose molecules. This process is fundamental 
        to life on Earth as it provides the primary source of energy for most ecosystems.

        The process occurs in two main stages: the light-dependent reactions and the light-independent 
        reactions (Calvin cycle). During the light-dependent reactions, chlorophyll and other pigments 
        absorb light energy, which is used to split water molecules and produce ATP and NADPH. 

        In the Calvin cycle, carbon dioxide from the atmosphere is fixed into organic molecules using 
        the ATP and NADPH produced in the first stage. The overall equation for photosynthesis is:
        6CO2 + 6H2O + light energy → C6H12O6 + 6O2

        Photosynthesis not only provides energy for plants but also produces oxygen as a byproduct, 
        which is essential for the survival of most living organisms on Earth.
        """,
        author="Dr. Emily Smith",
        doc_type="textbook_chapter"
    )
    
    course_library.add_course_document(
        course_id=course_id,
        title="Cellular Respiration and Energy Production",
        content="""
        Cellular respiration is the process by which cells break down glucose and other organic molecules 
        to release energy in the form of ATP (adenosine triphosphate). This process is essentially the 
        opposite of photosynthesis and occurs in all living organisms.

        Cellular respiration consists of three main stages:
        1. Glycolysis: Glucose is broken down into pyruvate in the cytoplasm
        2. Krebs Cycle (Citric Acid Cycle): Pyruvate is further broken down in the mitochondria
        3. Electron Transport Chain: The final stage where most ATP is produced

        The overall equation for cellular respiration is:
        C6H12O6 + 6O2 → 6CO2 + 6H2O + ATP

        This process is crucial for providing energy for all cellular activities, from muscle contraction 
        to protein synthesis. Understanding the relationship between photosynthesis and cellular respiration 
        helps students grasp the fundamental energy cycles that sustain life.
        """,
        author="Dr. Michael Johnson",
        doc_type="lecture_notes"
    )
    
    course_library.add_course_document(
        course_id=course_id,
        title="Plant Cell Structure and Function",
        content="""
        Plant cells have several unique structures that distinguish them from animal cells. The most 
        notable features include the cell wall, chloroplasts, and large central vacuole.

        The cell wall provides structural support and protection, made primarily of cellulose. 
        Chloroplasts are the organelles where photosynthesis occurs, containing the green pigment 
        chlorophyll that captures light energy.

        The central vacuole serves multiple functions including maintaining turgor pressure, 
        storing water and nutrients, and providing structural support. These adaptations allow 
        plants to perform photosynthesis efficiently and maintain their structure without a skeletal system.

        Understanding plant cell structure is essential for comprehending how photosynthesis works 
        at the cellular level and how plants have evolved to capture and convert solar energy.
        """,
        author="Dr. Sarah Wilson",
        doc_type="study_guide"
    )
    
    print(f"Example course '{course_id}' set up with {len(course_library.course_libraries[course_id])} documents")
    return course_id

def run_example():
    """Run an example of the system"""
    # Set up example course
    course_id = setup_example_course()
    
    # Example input text
    input_text = """
    Photosynthesis is a fundamental biological process used by green plants, algae, and some bacteria to convert 
    light energy, usually from the sun, into chemical energy stored in glucose. During this process, organisms absorb 
    carbon dioxide from the air and water from the soil. Using sunlight captured by chlorophyll—the green pigment in 
    plant cells—they convert these raw materials into glucose, a type of sugar that serves as food, and release oxygen 
    as a byproduct. This process not only sustains the plant's growth and energy needs but also produces the oxygen essential 
    for the survival of most living organisms on Earth.
    """
    
    print("\n" + "="*80)
    print("READING APPRENTICESHIP QUESTION GENERATOR")
    print("="*80)
    print(f"\nCourse ID: {course_id}")
    print(f"Input Text: {input_text[:100]}...")
    
    # Create input state
    input_state = SharedInput(
        input=input_text,
        course_id=course_id
    )
    
    # Run the workflow
    print("\nRunning workflow...")
    result = workflow_app.invoke(input_state)
    
    # Display results
    print("\n" + "-"*60)
    print("STEP 1: EXTRACTED INFORMATION")
    print("-"*60)
    print(result.get("extracted_info", "No extracted info"))
    
    print("\n" + "-"*60)
    print("STEP 2: RELEVANT COURSE CONTEXT")
    print("-"*60)
    print(result.get("relevant_context", "No context found"))
    
    print("\n" + "-"*60)
    print("STEP 3: GENERATED QUESTIONS")
    print("-"*60)
    print(result.get("questions", "No questions generated"))
    
    print("\n" + "-"*60)
    print("STEP 4: TEACHER PROMPTS")
    print("-"*60)
    print(result.get("prompts", "No prompts generated"))
    
    print("\n" + "-"*60)
    print("STEP 5: QUALITY EVALUATION")
    print("-"*60)
    print(result.get("evaluation", "No evaluation"))
    
    print("\n" + "="*80)
    print("WORKFLOW COMPLETED SUCCESSFULLY!")
    print("="*80)

if __name__ == "__main__":
    # Check if required environment variables are set
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY not found in environment variables.")
        print("Please set your Google API key in a .env file or environment variable.")
        print("Example .env file:")
        print("GOOGLE_API_KEY=your_google_api_key_here")
    else:
        run_example()