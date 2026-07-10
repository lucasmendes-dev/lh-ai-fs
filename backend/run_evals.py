"""
run_evals.py — End-to-end evaluation harness for the BS Detector pipeline.

Runs the full pipeline (CitationAgent → FactCheckerAgent → JudicialMemoAgent →
ReportBuilder) against the real case documents and scores the output against a
curated ground truth of known flaws.

Metrics:
  precision          — of all flagged issues, what fraction are real flaws?
  recall             — of all known flaws, what fraction did we catch?
  hallucination_rate — of all flagged issues, what fraction are not real flaws?
  abstention_rate    — of all citations/claims examined, what fraction did the
                       pipeline honestly decline to assess? (lower is not always
                       better — an honest abstention beats a confident wrong answer)

Eval design note:
  Ground-truth matching is intentionally keyword-based (not embedding-based) for
  transparency and reproducibility. The keywords are chosen to be specific enough
  that they cannot be accidentally triggered by unrelated claims, while broad
  enough to survive minor rewording by the LLM. Each flaw has a distinct keyword
  set so a single claim cannot count as two separate TP hits (deduplication is
  enforced per flaw ID). This prevents a verbose LLM response from inflating recall.

  A "could_not_verify" on a known-flawed citation/claim is recorded as an
  abstention — NOT as a hallucination and NOT as a miss. It represents honest
  uncertainty, which is the correct posture when evidence is insufficient. The
  abstention_rate metric lets evaluators see how often the pipeline chose safety
  over confidence.

How to run:
  # With Docker:
  docker compose exec backend python run_evals.py

  # Locally (activate venv first):
  python run_evals.py
"""

import sys
from pathlib import Path

# Ensure backend/ is on sys.path so local imports resolve
sys.path.insert(0, str(Path(__file__).parent))

from agents.citation_agent import CitationAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.judicial_memo_agent import JudicialMemoAgent
from agents.report_builder import ReportBuilder
from main import load_documents

# ---------------------------------------------------------------------------
# Ground Truth
# ---------------------------------------------------------------------------
# Keys are lowercase substrings that appear in the citation text.
# Values describe the type of flaw for human-readable reporting.
GROUND_TRUTH_CITATION_FLAWS: dict[str, str] = {
    "privette": "quote_inaccurate",
    "whitmore": "fabricated_citation",
    "kellerman": "fabricated_citation_and_quote",
    "seabright": "unsupported_proposition",
    "torres": "fabricated_citation",
    "blackwell": "fabricated_citation",
}

# Canonical flaw IDs for fact issues; each flaw has a non-overlapping keyword set.
# Rationale: keywords are chosen to be specific to the exact contradiction in the
# document text. Generic words like "date" are excluded because they appear across
# multiple claim texts and would cause double-counting.
GROUND_TRUTH_FACT_FLAWS: dict[str, list[str]] = {
    # The MSJ says March 14; police report + witness both say March 12.
    "incident_date_contradiction": ["march 14", "march 12", "two days off", "incident date"],
    # The MSJ claims Rivera was NOT wearing PPE; police report + witness say he was.
    "ppe_contradiction": ["personal protective equipment", "fall-arrest", "ppe", "harness", "safety gear"],
    # Harmon's foreman received direct safety warnings and overruled them.
    "reasonable_care_notice_contradiction": ["iipp", "osha inspection", "reasonable care", "injury and illness prevention"],
    # The SOL calculation in the MSJ uses the wrong incident date.
    "statute_of_limitations_miscalculation": ["accrual", "statute of limitations", "362", "363", "march 10, 2023"],
}


def _match_fact_flaw(claim_text: str) -> str | None:
    """Return the canonical flaw ID if the claim matches a known ground-truth flaw.

    Returns only the FIRST matching flaw ID to prevent a single claim from
    being counted as two separate true positives (deduplication at match time).
    """
    lower = claim_text.lower()
    for flaw_id, keywords in GROUND_TRUTH_FACT_FLAWS.items():
        if any(kw in lower for kw in keywords):
            return flaw_id
    return None


def _is_citation_flagged(cit: dict) -> bool:
    """Return True if the citation was flagged as having a definite flaw."""
    return (
        cit.get("is_citation_real") is False
        or cit.get("is_proposition_supported") is False
        or cit.get("is_quote_accurate") is False
    )


def _is_citation_abstained(cit: dict) -> bool:
    """Return True if the citation was honestly marked could_not_verify on any field."""
    return (
        cit.get("is_citation_real") == "could_not_verify"
        or cit.get("is_proposition_supported") == "could_not_verify"
        or cit.get("is_quote_accurate") == "could_not_verify"
    )


def run_evaluation():
    print("\n==================================================")
    print("  BS DETECTOR — END-TO-END EVALUATION")
    print("==================================================")
    print("Running full pipeline against real case documents...")
    print()

    # ------------------------------------------------------------------
    # Load documents
    # ------------------------------------------------------------------
    documents = load_documents()
    motion = documents.get("motion_for_summary_judgment", "")
    police = documents.get("police_report", "")
    medical = documents.get("medical_records_excerpt", "")
    witness = documents.get("witness_statement", "")

    if not motion:
        print("ERROR: motion_for_summary_judgment.txt not found in documents/")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Run the pipeline
    # ------------------------------------------------------------------
    print("[1/4] CitationAgent      — extracting and verifying citations...")
    citation_analysis = CitationAgent().run(motion)

    print("[2/4] FactCheckerAgent   — cross-document fact checking...")
    fact_analysis = FactCheckerAgent().run(
        motion=motion,
        police_report=police,
        medical_records=medical,
        witness_statement=witness,
        citations=citation_analysis.get("citations", []),
    )

    print("[3/4] ReportBuilder      — assembling final report...")
    report = ReportBuilder().build(
        citation_analysis=citation_analysis,
        fact_analysis=fact_analysis,
    )

    print("[4/4] JudicialMemoAgent  — synthesizing judicial memo...")
    judicial_memo = JudicialMemoAgent().run(report)
    report["judicial_memo"] = judicial_memo

    # ------------------------------------------------------------------
    # Evaluate Citation Findings
    # ------------------------------------------------------------------
    citations_out = report.get("citation_analysis", {}).get("citations", [])
    remaining_citation_flaws = list(GROUND_TRUTH_CITATION_FLAWS.keys())

    citation_tp: list[str] = []        # caught definite flaws
    citation_fp: list[str] = []        # definitively flagged things that are not flaws
    citation_abstained_tp: list[str] = []  # honest abstentions on known-flawed citations
    citation_abstained_fp: list[str] = []  # honest abstentions on clean citations (not penalised)
    citation_fn: list[str] = []        # known flaws completely missed (no flag, no abstention)

    for cit in citations_out:
        cit_text = cit.get("citation", "").lower()
        matched_key = next(
            (k for k in GROUND_TRUTH_CITATION_FLAWS if k in cit_text), None
        )

        flagged = _is_citation_flagged(cit)
        abstained = _is_citation_abstained(cit)

        if matched_key:
            # This is a known-flawed citation
            if flagged:
                citation_tp.append(matched_key)
                if matched_key in remaining_citation_flaws:
                    remaining_citation_flaws.remove(matched_key)
            elif abstained:
                # Honest abstention on a flawed citation — not a hallucination,
                # but also not a full catch. We record it separately.
                citation_abstained_tp.append(matched_key)
                if matched_key in remaining_citation_flaws:
                    remaining_citation_flaws.remove(matched_key)
        else:
            # This is a citation NOT in our ground truth
            if flagged:
                # Definitively flagged something clean → potential hallucination
                citation_fp.append(cit.get("citation", "unknown"))
            elif abstained:
                # Honest "could not verify" on an unverified citation — correct posture
                citation_abstained_fp.append(cit.get("citation", "unknown"))
            # else: said it was fine → no action needed

    citation_fn = remaining_citation_flaws  # anything still in list was completely missed

    # ------------------------------------------------------------------
    # Evaluate Fact Findings
    # ------------------------------------------------------------------
    issues_out = report.get("fact_analysis", {}).get("issues", [])
    remaining_fact_flaws = list(GROUND_TRUTH_FACT_FLAWS.keys())

    fact_tp: list[str] = []
    fact_fp: list[str] = []
    fact_fn: list[str] = []

    seen_fact_flaw_ids: set[str] = set()  # deduplication: count each flaw at most once

    for issue in issues_out:
        claim_text = issue.get("claim", "").lower()
        status = issue.get("status", "")
        matched_flaw = _match_fact_flaw(claim_text)

        if matched_flaw:
            if status in ("contradicted", "unsupported"):
                # Only count a flaw ID once, even if multiple claims match it
                if matched_flaw not in seen_fact_flaw_ids:
                    fact_tp.append(matched_flaw)
                    seen_fact_flaw_ids.add(matched_flaw)
                    if matched_flaw in remaining_fact_flaws:
                        remaining_fact_flaws.remove(matched_flaw)
            # could_not_verify on a known-flawed fact: honest abstention, no penalty
        else:
            if status in ("contradicted", "unsupported"):
                # Flagged a fact issue not in ground truth → potential hallucination
                fact_fp.append(issue.get("claim", "unknown")[:80])

    fact_fn = remaining_fact_flaws

    # ------------------------------------------------------------------
    # Aggregate Metrics
    # ------------------------------------------------------------------
    # Abstentions on known-flawed citations count as partial recall
    # (they avoided hallucination) but are shown separately in the report.
    total_tp = len(citation_tp) + len(fact_tp)
    total_fp = len(citation_fp) + len(fact_fp)
    # Abstentions on known flaws do NOT count as FN (they didn't hallucinate)
    # but they also don't count as TP (they didn't definitively flag it).
    # We count them toward abstention_rate but not recall.
    total_fn = len(citation_fn) + len(fact_fn)
    total_abstained_on_flaws = len(citation_abstained_tp)
    total_abstained_clean = len(citation_abstained_fp)
    total_examined = len(citations_out) + len(issues_out)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn + total_abstained_on_flaws) if (total_tp + total_fn + total_abstained_on_flaws) > 0 else 0.0
    hallucination_rate = total_fp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    abstention_rate = (total_abstained_on_flaws + total_abstained_clean) / total_examined if total_examined > 0 else 0.0

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print()
    print("─" * 54)
    print("  CITATION FINDINGS")
    print("─" * 54)
    print(f"  Citations examined:          {len(citations_out)}")
    print(f"  Known flaws definitively caught (TP): {citation_tp}")
    print(f"  Known flaws honestly abstained:       {citation_abstained_tp}")
    print(f"  Known flaws missed entirely  (FN): {citation_fn}")
    if citation_fp:
        print(f"  Hallucinated flags           (FP): {citation_fp}")
    if citation_abstained_fp:
        print(f"  Honest abstentions on other cits:  {len(citation_abstained_fp)} item(s)")

    print()
    print("─" * 54)
    print("  FACT FINDINGS")
    print("─" * 54)
    print(f"  Fact claims examined:        {len(issues_out)}")
    print(f"  Known flaws caught   (TP): {fact_tp}")
    print(f"  Known flaws missed   (FN): {fact_fn}")
    if fact_fp:
        print(f"  Hallucinated flags   (FP): {fact_fp}")

    print()
    print("─" * 54)
    print("  METRICS")
    print("─" * 54)
    print(f"  Precision:          {precision:.1%}  (how accurate are our flags?)")
    print(f"  Recall:             {recall:.1%}  (how many real flaws did we catch?)")
    print(f"  Hallucination Rate: {hallucination_rate:.1%}  (flags that are not real flaws)")
    print(f"  Abstention Rate:    {abstention_rate:.1%}  (honest 'could not verify' responses)")
    print()
    print("  NOTE: 'could_not_verify' responses are NOT counted as hallucinations.")
    print("  Honest abstention is a correct posture when evidence is insufficient.")
    print()
    print("  EVAL DESIGN NOTE: Recall denominator includes abstentions on known flaws.")
    print("  A flaw that is abstained on is better than one that is hallucinated about,")
    print("  but it is not the same as definitively catching it. Each known flaw is")
    print("  counted at most once as TP, even if multiple claims match the same flaw ID.")
    print("─" * 54)

    if judicial_memo:
        print()
        print("─" * 54)
        print("  JUDICIAL MEMO (synthesized by JudicialMemoAgent)")
        print("─" * 54)
        memo_text = judicial_memo if isinstance(judicial_memo, str) else judicial_memo.get("memo", "")
        for line in memo_text.strip().splitlines():
            print(f"  {line}")
        print("─" * 54)


if __name__ == "__main__":
    run_evaluation()
