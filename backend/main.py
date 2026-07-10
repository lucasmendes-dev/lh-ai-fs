from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from agents.citation_agent import CitationAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.judicial_memo_agent import JudicialMemoAgent
from agents.report_builder import ReportBuilder

app = FastAPI(title="BS Detector API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS_DIR = Path(__file__).parent / "documents"


def load_documents() -> dict[str, str]:
    """Load all documents from the documents directory."""
    documents = {}
    for file_path in DOCUMENTS_DIR.glob("*.txt"):
        documents[file_path.stem] = file_path.read_text()
    return documents


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "bs-detector-api"}


@app.post("/analyze")
async def analyze():
    """
    Run the full BS Detector pipeline against the case documents.

    Pipeline:
      1. CitationAgent   — extract and verify all legal citations
      2. FactCheckerAgent — cross-document fact checking
      3. ReportBuilder   — assemble report with summary stats and risk level
      4. JudicialMemoAgent — synthesize a one-paragraph judicial memo

    Returns a structured verification report with citation findings,
    fact issues, summary statistics, risk level, and a judicial memo.
    """
    documents = load_documents()

    motion = documents["motion_for_summary_judgment"]
    police = documents["police_report"]
    medical = documents["medical_records_excerpt"]
    witness = documents["witness_statement"]

    citation_agent = CitationAgent()
    fact_checker_agent = FactCheckerAgent()
    report_builder = ReportBuilder()
    judicial_memo_agent = JudicialMemoAgent()

    citation_analysis = citation_agent.run(motion)

    fact_analysis = fact_checker_agent.run(
        motion=motion,
        police_report=police,
        medical_records=medical,
        witness_statement=witness,
        citations=citation_analysis.get("citations", []),
    )

    report = report_builder.build(
        citation_analysis=citation_analysis,
        fact_analysis=fact_analysis,
    )

    judicial_memo = judicial_memo_agent.run(report)
    report["judicial_memo"] = judicial_memo

    return {"report": report}
