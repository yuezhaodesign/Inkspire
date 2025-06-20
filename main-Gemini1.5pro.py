from langgraph.graph import StateGraph
from langchain.schema import HumanMessage
from langchain_core.runnables import Runnable
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI  # Changed here

# Load environment variables
load_dotenv()

# Initialize Gemini 1.5 Pro
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0.3)




# Define the state schema
class SharedInput(BaseModel):
    input: str
    extracted_info: str = None
    questions: str = None
    evaluation: str = None

# Agent A: Extract Information
class ExtractorAgent(Runnable):
    def invoke(self, state, config=None):  # Accept `config` as the second argument
        prompt = f"Extract the main ideas and keywords from this text:\n\n{state.input}"
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"extracted_info": response.content}


# Agent B: Generate Questions
class ScaffoldAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = (
            "Based on the following information, generate 4 comprehension questions, aligned with social, personal, cognitive, knowledge-building dimensions of the "
            "Reading Apprenticeship framework:\n\n"
            "- **Social**: Promotes discussion or collaborative thinking\n"
            "- **Personal**: Invites self-reflection or personal connection\n"
            "- **Cognitive**: Encourages metacognition or strategy use\n"
            "- **Knowledge-Building**: Deepens understanding of concepts or information\n\n"
            f"Text:\n{state.extracted_info}\n\n"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"questions": response.content}

# Agent C: Quality Checker
class QualityAgent(Runnable):
    def invoke(self, state, config=None):
        prompt = (
            "Evaluate the following comprehension questions in terms of how well each aligns with the dimensions of the "
            "Reading Apprenticeship (RA) framework: Social, Personal, Cognitive, and Knowledge-Building.\n\n"
            "For each question:\n"
            "- Identify which RA dimension it most aligns with\n"
            "- Justify the alignment in 1–2 sentences\n"
            "- Evaluate whether the question is clear, relevant, and promotes meaningful thinking\n\n"
            f"Questions:\n{state.questions}\n\n"
            "Return your evaluation in a clear and structured format."
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"evaluation": response.content}


# Create the LangGraph workflow with schema
workflow = StateGraph(SharedInput)

# Add nodes (agents)
workflow.add_node("extractor", ExtractorAgent())
workflow.add_node("scaffold", ScaffoldAgent())
workflow.add_node("quality", QualityAgent())

# Define the flow: extractor → scaffold → quality
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "scaffold")
workflow.add_edge("scaffold", "quality")
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

    # Print all intermediate outputs
    print("Step 1: Extracted Info")
    print(result.get("extracted_info", "[missing]"), "\n")

    print("Step 2: Generated Questions")
    print(result.get("questions", "[missing]"), "\n")

    print("Step 3: Quality Evaluation")
    print(result.get("evaluation", "[missing]"))
