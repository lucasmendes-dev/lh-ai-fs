from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from agents.citation_agent import CitationAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.report_builder import ReportBuilder

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
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


@app.post("/analyze")
async def analyze():
    documents = load_documents()

    motion = documents["motion_for_summary_judgment"]
    police = documents["police_report"]
    medical = documents["medical_records_excerpt"]
    witness = documents["witness_statement"]

    citation_agent = CitationAgent()
    fact_checker_agent = FactCheckerAgent()
    report_builder = ReportBuilder()

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

    return {"report": report}
