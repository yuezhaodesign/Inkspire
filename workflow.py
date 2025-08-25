from __future__ import annotations
import os, logging, argparse
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph
from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)

# -------------------- setup --------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("RA-RAG")
load_dotenv()

LLM = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
EMB = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
SPLIT = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)

def ask_llm(prompt: str) -> str:
    return LLM.invoke([HumanMessage(content=prompt)]).content

# -------------------- state --------------------
class State(BaseModel):
    # Inputs
    reading_a: Dict[str, str] = Field(..., description="{'title','author','content'} – do NOT chunk")
    learning_objectives: List[str] = Field(default_factory=list)
    reading_b: List[Dict[str, str]] = Field(default_factory=list, description="List of {'title','author','content'} to RAG")

    # Artifacts
    a_keywords: Optional[str] = None
    a_key_sentences: Optional[str] = None
    rag_context: Optional[str] = None
    annotations: Optional[str] = None
    evaluation: Optional[str] = None

# -------------------- file loading --------------------
SUPPORTED_EXTS = {".pdf", ".txt", ".docx", ".doc"}

def load_file_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        pages = PyPDFLoader(str(path)).load()
        return "\n".join(p.page_content for p in pages)
    elif ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    elif ext in {".docx", ".doc"}:
        docs = Docx2txtLoader(str(path)).load()
        return "\n".join(d.page_content for d in docs)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def to_reading_dict_from_file(path: Path, title: Optional[str] = None, author: str = "Unknown") -> Dict[str, str]:
    text = load_file_text(path)
    return {
        "title": title or path.stem,
        "author": author,
        "content": text,
    }

def load_reading_b_folder(folder: Path, author: str = "Unknown") -> List[Dict[str, str]]:
    docs: List[Dict[str, str]] = []
    if not folder.exists() or not folder.is_dir():
        log.warning("Reading B folder %s does not exist or is not a directory.", folder)
        return docs
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            try:
                docs.append(to_reading_dict_from_file(p, title=p.stem, author=author))
                log.info("Loaded Reading B: %s", p.name)
            except Exception as e:
                log.warning("Skipping %s (%s)", p.name, e)
    return docs

def load_objectives_file(path: Optional[Path]) -> List[str]:
    if not path:
        return []
    if not path.exists():
        log.warning("Objectives file %s not found; continuing with empty objectives.", path)
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    # keep non-empty lines
    return [ln.strip() for ln in lines if ln.strip()]

# -------------------- RAG store (InMemoryVectorStore) --------------------
class RAGStore:
    """In-memory vector store for Reading B only (no web)."""
    def __init__(self):
        self.vs = InMemoryVectorStore(embedding=EMB)

    def add_docs(self, docs: List[Document]):
        if docs:
            self.vs.add_documents(docs)

    def retrieve(self, query: str, k: int = 8) -> List[Document]:
        # Use the modern invoke API (avoids deprecation warning)
        retriever = self.vs.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)

RAG = RAGStore()

def b_to_docs(blobs: List[Dict[str,str]]) -> List[Document]:
    docs: List[Document] = []
    for b in blobs:
        meta = {"title": b.get("title",""), "author": b.get("author","")}
        for chunk in SPLIT.split_text(b.get("content","") or ""):
            docs.append(Document(page_content=chunk, metadata=meta))
    return docs

# -------------------- Agents --------------------
class AgentA_ExtractFromA(Runnable):
    """Reading A: NO chunking. Extract keywords and select key sentences."""
    def invoke(self, s: State, config=None):
        content = s.reading_a.get("content","")
        title = s.reading_a.get("title","")
        kws = ask_llm(
            "Extract 10–20 keywords/terms (comma-separated) that best represent the reading.\n"
            f"TITLE: {title}\nTEXT:\n{content}"
        )
        key_sents = ask_llm(
            "Select 5–8 key sentences from the reading that are high-leverage for instruction. "
            "Return ONLY the sentences as a numbered list (1..n). Prefer definitional, causal, or summary sentences.\n\n"
            f"TITLE: {title}\nTEXT:\n{content}"
        )
        return {"a_keywords": kws, "a_key_sentences": key_sents}

class AgentB_RAG_ForA(Runnable):
    """
    RAG from Reading B only. Use learning objectives + A keywords to retrieve context.
    Generate annotations: for each key sentence from A, create a Prompt + RA-tagged Question.
    """
    def invoke(self, s: State, config=None):
        # Ingest Reading B into in-memory vector store
        RAG.add_docs(b_to_docs(s.reading_b))

        # Retrieve context with objectives + A keywords
        lo_text = " | ".join(s.learning_objectives) if s.learning_objectives else ""
        query = (s.a_keywords or "") + " " + lo_text
        docs = RAG.retrieve(query, k=8)
        ctx = "\n\n---\n\n".join(
            f"Title: {d.metadata.get('title','')}\nSource: {d.metadata.get('author','')}\nExcerpt: {d.page_content[:700]}..."
            for d in docs
        ) or "No external context."

        lo_block = "\n".join(f"- {o}" for o in s.learning_objectives) or "(none provided)"
        prompt = (
            "You are scaffolding **Reading A**.\n"
            "Given KEY SENTENCES from Reading A (no chunking) and RAG context from Reading B only, "
            "produce **annotations** where EACH key sentence is paired with:\n"
            "- a short **Teacher Prompt** (1–2 sentences) and\n"
            "- an **RA-aligned Question** tagged as Social/Personal/Cognitive/Knowledge-Building.\n\n"
            "FORMAT EXACTLY:\n"
            "Annotations:\n"
            "1) Sentence: \"...\"\n   Prompt: ...\n   Question (RA: Dimension): ...\n"
            "2) Sentence: \"...\"\n   Prompt: ...\n   Question (RA: Dimension): ...\n"
            "(continue for all provided key sentences)\n\n"
            "CONSTRAINTS:\n"
            "- Ground questions in Reading A; use RAG only to deepen/contrast.\n"
            "- Distribute RA dimensions across items (aim for balance).\n"
            "- Align to the teacher’s learning objectives.\n\n"
            f"Reading A — Key Sentences:\n{s.a_key_sentences}\n\n"
            f"Learning Objectives:\n{lo_block}\n\n"
            f"RAG Context (Reading B only):\n{ctx}\n"
        )
        annotations = ask_llm(prompt)
        return {"rag_context": ctx, "annotations": annotations}

class AgentC_QualityCheck(Runnable):
    """Evaluate alignment to objectives, RA balance, and fidelity to Reading A. Provide fixes."""
    def invoke(self, s: State, config=None):
        review = ask_llm(
            "Quality-check the annotations below. Assess: (a) alignment to objectives, "
            "(b) fidelity to Reading A sentences, (c) RA balance and clarity. Then list concrete improvements.\n\n"
            f"Learning Objectives:\n" + "\n".join(f"- {o}" for o in s.learning_objectives) + "\n\n"
            f"Annotations:\n{s.annotations}\n"
        )
        return {"evaluation": review}

# -------------------- Graph --------------------
def build_workflow():
    g = StateGraph(State)
    g.add_node("A_extract",  AgentA_ExtractFromA())
    g.add_node("B_generate", AgentB_RAG_ForA())
    g.add_node("C_quality",  AgentC_QualityCheck())
    g.set_entry_point("A_extract")
    g.add_edge("A_extract", "B_generate")
    g.add_edge("B_generate", "C_quality")
    g.set_finish_point("C_quality")
    return g.compile()

workflow = build_workflow()

# -------------------- CLI --------------------
def main():
    parser = argparse.ArgumentParser(description="RA RAG Workflow (no web)")
    parser.add_argument("--reading-a", required=True, help="Path to Reading A file (.pdf/.txt/.docx/.doc)")
    parser.add_argument("--reading-b-dir", required=True, help="Directory containing Reading B files")
    parser.add_argument("--objectives-file", required=False, help="Optional path to a .txt file (one objective per line)")
    parser.add_argument("--reading-a-title", required=False, help="Optional title override for Reading A")
    parser.add_argument("--reading-a-author", required=False, default="Unknown", help="Optional author for Reading A")
    parser.add_argument("--reading-b-author", required=False, default="Unknown", help="Optional author label for Reading B items")
    args = parser.parse_args()

    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("Please set GOOGLE_API_KEY in your environment and re-run.")

    a_path = Path(args.reading_a)
    b_dir = Path(args.reading_b_dir)
    obj_path = Path(args.objectives_file) if args.objectives_file else None

    # Load Reading A
    reading_a = to_reading_dict_from_file(a_path, title=args.reading_a_title or a_path.stem, author=args.reading_a_author)
    # Load all Reading B files in folder
    reading_b = load_reading_b_folder(b_dir, author=args.reading_b_author)
    # Load objectives
    objectives = load_objectives_file(obj_path)

    if not reading_b:
        log.warning("No Reading B files were loaded from %s. RAG context may be empty.", b_dir)
    if not objectives:
        log.warning("No objectives provided. Generation will proceed, but alignment may be generic.")

    # Run workflow
    state = State(reading_a=reading_a, reading_b=reading_b, learning_objectives=objectives)
    result = workflow.invoke(state)

    # Print outputs
    print("\n=== KEYWORDS (A) ===\n", result.get("a_keywords"))
    print("\n=== KEY SENTENCES (A) ===\n", result.get("a_key_sentences"))
    print("\n=== RAG CONTEXT (B only) ===\n", (result.get("rag_context") or "")[:1500], "...")
    print("\n=== ANNOTATIONS ===\n", result.get("annotations"))
    print("\n=== QUALITY REVIEW ===\n", result.get("evaluation"))

if __name__ == "__main__":
    main()
