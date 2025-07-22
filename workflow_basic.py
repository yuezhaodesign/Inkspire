from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# Define the state schema
class SharedInput(BaseModel):
    input: str
    extracted_info: str = None
    questions: str = None
    prompts: str = None
    evaluation: str = None

# Agent A: Extract Information
class ExtractorAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = f"Extract the main ideas and keywords from this text:\n\n{state.input}"
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"extracted_info": response.content}

# Agent B: Generate Questions and Teacher Prompts
class ScaffoldPromptAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = (
            "Based on the following information, do the following:\n\n"
            "1. Generate 4 comprehension questions aligned with the social, personal, cognitive, and knowledge-building dimensions of the Reading Apprenticeship (RA) framework.\n"
            "   - Social: Promotes discussion or collaborative thinking\n"
            "   - Personal: Invites self-reflection or personal connection\n"
            "   - Cognitive: Encourages metacognition or strategy use\n"
            "   - Knowledge-Building: Deepens understanding of concepts or information\n\n"
            "2. For each question, create a short teacher prompt (1–2 sentences) that guides the teacher to facilitate discussion or thinking about the question with students.\n\n"
            "Format your answer as follows:\n"
            "Questions:\n1. ...\n2. ...\n3. ...\n4. ...\n\n"
            "Prompts:\n1. ...\n2. ...\n3. ...\n4. ...\n\n"
            f"Information:\n{state.extracted_info}\n"
        )
        response = llm.invoke([HumanMessage(content=prompt)])

        # Split output into questions and prompts
        output = response.content
        try:
            questions_part = output.split("Prompts:")[0].replace("Questions:", "").strip()
            prompts_part = output.split("Prompts:")[1].strip()
        except Exception:
            questions_part = output
            prompts_part = ""
        return {
            "questions": questions_part,
            "prompts": prompts_part
        }

# Agent C: Quality Check
class QualityAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = (
            "Evaluate the following comprehension questions and teacher prompts in terms of how well they align with the dimensions of the "
            "Reading Apprenticeship (RA) framework: Social, Personal, Cognitive, and Knowledge-Building.\n\n"
            "For each question:\n"
            "- Identify which RA dimension it most aligns with\n"
            "- Justify the alignment in 1–2 sentences\n"
            "- Evaluate whether the question is clear, relevant, and promotes meaningful thinking\n\n"
            "For each teacher prompt:\n"
            "- Evaluate if it effectively guides the teacher to facilitate student discussion or thinking\n"
            "- Check if it supports deeper understanding or useful connections\n\n"
            f"Questions:\n{state.questions}\n\nPrompts:\n{state.prompts}\n\n"
            "Return your evaluation in a structured, readable format."
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"evaluation": response.content}

# Create the LangGraph workflow
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
app = workflow.compile()

# Run a test
if __name__ == "__main__":
    input_text = (
        "Photosynthesis is a fundamental biological process used by green plants, algae, and some bacteria to convert "
        "light energy, usually from the sun, into chemical energy stored in glucose. During this process, organisms absorb "
        "carbon dioxide from the air and water from the soil. Using sunlight captured by chlorophyll—the green pigment in "
        "plant cells—they convert these raw materials into glucose, a type of sugar that serves as food, and release oxygen "
        "as a byproduct. This process not only sustains the plant's growth and energy needs but also produces the oxygen essential "
        "for the survival of most living organisms on Earth."
    )
    input_state = SharedInput(input=input_text)
    result = app.invoke(input_state)

    print("Step 1: Extracted Info")
    print(result.get("extracted_info", "[missing]"), "\n")

    print("Step 2: Generated Questions")
    print(result.get("questions", "[missing]"), "\n")

    print("Step 3: Generated Prompts")
    print(result.get("prompts", "[missing]"), "\n")

    print("Step 4: Quality Evaluation")
    print(result.get("evaluation", "[missing]"))
