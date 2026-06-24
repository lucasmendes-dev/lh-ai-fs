import os
import sys
from pathlib import Path

# Add backend directory to path to ensure proper imports
sys.path.append(str(Path(__file__).parent))

from agents.citation_agent import CitationAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.report_builder import ReportBuilder
from main import load_documents

# Ground Truth definition of flaws in the case file
# A flaw is either a citation issue (invalid, unsupported, inaccurate quote) or a factual contradiction.
GROUND_TRUTH_CITATION_FLAWS = {
    "privette": "quote_inaccurate",
    "whitmore": "fabricated_citation",
    "kellerman": "fabricated_citation_and_quote",
    "seabright": "unsupported_proposition",
    "torres": "fabricated_citation",
    "blackwell": "fabricated_citation"
}

GROUND_TRUTH_FACT_FLAWS = {
    "date": "incident_date_contradiction",
    "ppe": "ppe_contradiction",
    "safety": "ppe_contradiction",
    "harness": "ppe_contradiction",
    "osha": "reasonable_care_notice_contradiction",
    "care": "reasonable_care_notice_contradiction",
    "accrual": "statute_of_limitations_miscalculation",
    "limitations": "statute_of_limitations_miscalculation"
}

def run_evaluation(mode: str):
    print(f"\n==================================================")
    print(f"RUNNING EVALUATION IN MODE: {mode.upper()}")
    print(f"==================================================")

    # Set the environment variable for the mock LLM
    os.environ["EVAL_MODE"] = mode

    # Load documents
    documents = load_documents()
    motion = documents.get("motion_for_summary_judgment", "")
    police = documents.get("police_report", "")
    medical = documents.get("medical_records_excerpt", "")
    witness = documents.get("witness_statement", "")

    # Instantiate agents
    citation_agent = CitationAgent()
    fact_checker_agent = FactCheckerAgent()
    report_builder = ReportBuilder()

    # Run the pipeline
    print("Running CitationAgent...")
    citation_analysis = citation_agent.run(motion)
    
    print("Running FactCheckerAgent...")
    fact_analysis = fact_checker_agent.run(
        motion=motion,
        police_report=police,
        medical_records=medical,
        witness_statement=witness,
        citations=citation_analysis.get("citations", [])
    )

    print("Building final report...")
    report = report_builder.build(
        citation_analysis=citation_analysis,
        fact_analysis=fact_analysis
    )

    # Evaluate Citation Flaws
    tp_citations = []
    fp_citations = []
    fn_citations = list(GROUND_TRUTH_CITATION_FLAWS.keys())

    for cit in report.get("citation_analysis", {}).get("citations", []):
        cit_text = cit.get("citation", "").lower()
        matched_gt_key = None
        for gt_key in GROUND_TRUTH_CITATION_FLAWS.keys():
            if gt_key in cit_text:
                matched_gt_key = gt_key
                break

        # If it's a known ground truth case
        if matched_gt_key:
            # Check if we flagged an issue
            is_flawed = (
                cit.get("is_citation_real") is False or
                cit.get("is_proposition_supported") is False or
                cit.get("is_quote_accurate") is False
            )
            if is_flawed:
                tp_citations.append(matched_gt_key)
                if matched_gt_key in fn_citations:
                    fn_citations.remove(matched_gt_key)
            else:
                # We analyzed it but said it had no flaws (even though ground truth says it is flawed)
                pass
        else:
            # We flagged a case that is not a known flaw in ground truth
            # If we claimed it has a flaw, it is a false positive (hallucination)
            is_flawed = (
                cit.get("is_citation_real") is False or
                cit.get("is_proposition_supported") is False or
                cit.get("is_quote_accurate") is False
            )
            if is_flawed:
                fp_citations.append(cit.get("citation"))

    # Evaluate Fact Flaws
    tp_facts = []
    fp_facts = []
    fn_facts = ["incident_date_contradiction", "ppe_contradiction", "reasonable_care_notice_contradiction", "statute_of_limitations_miscalculation"]

    for issue in report.get("fact_analysis", {}).get("issues", []):
        claim_text = issue.get("claim", "").lower()
        matched_flaw = None
        
        # Check matching keywords
        if "date" in claim_text or "march 14" in claim_text:
            matched_flaw = "incident_date_contradiction"
        elif "ppe" in claim_text or "protective" in claim_text or "harness" in claim_text:
            matched_flaw = "ppe_contradiction"
        elif "osha" in claim_text or "care" in claim_text or "safety" in claim_text:
            matched_flaw = "reasonable_care_notice_contradiction"
        elif "accrual" in claim_text or "limitations" in claim_text or "filing" in claim_text:
            matched_flaw = "statute_of_limitations_miscalculation"

        if matched_flaw:
            if issue.get("status") in ["contradicted", "unsupported"]:
                tp_facts.append(matched_flaw)
                if matched_flaw in fn_facts:
                    fn_facts.remove(matched_flaw)
        else:
            # Flagged a fact issue not in ground truth
            if issue.get("status") in ["contradicted", "unsupported"]:
                fp_facts.append(issue.get("claim"))

    # Calculate metrics
    total_tp = len(tp_citations) + len(tp_facts)
    total_fp = len(fp_citations) + len(fp_facts)
    total_fn = len(fn_citations) + len(fn_facts)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    hallucination_rate = total_fp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0

    print("\n------------------ RESULTS ------------------")
    print(f"True Positives (Caught Flaws): {total_tp}")
    print(f"False Positives (Hallucinations): {total_fp}")
    print(f"False Negatives (Missed Flaws): {total_fn}")
    print(f" -> Citation Flaws Caught: {tp_citations}")
    print(f" -> Citation Flaws Missed: {fn_citations}")
    if fp_citations:
        print(f" -> Citation False Positives: {fp_citations}")
    print(f" -> Fact Flaws Caught: {tp_facts}")
    print(f" -> Fact Flaws Missed: {fn_facts}")
    if fp_facts:
        print(f" -> Fact False Positives: {fp_facts}")
    print(f"\nMETRICS:")
    print(f"Precision:          {precision:.2%}")
    print(f"Recall:             {recall:.2%}")
    print(f"Hallucination Rate: {hallucination_rate:.2%}")
    print("---------------------------------------------")

if __name__ == "__main__":
    # Run in perfect mode
    run_evaluation("perfect")
    
    # Run in noisy/imperfect mode to show the metrics capturing quality variance
    run_evaluation("noisy")
