import json
import re
from llm import call_llm


def _extract_text(response: str) -> str:
    """Strip markdown fences and return clean text."""
    cleaned = re.sub(r"```(?:json)?\s*", "", response).strip().rstrip("`").strip()
    # If the LLM wrapped the memo in a JSON object, extract it
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed.get("memo", cleaned)
    except (json.JSONDecodeError, ValueError):
        pass
    return cleaned


class JudicialMemoAgent:
    """Synthesizes the top findings into a one-paragraph judicial memo.

    Tier 3 requirement: this agent receives the structured output from the
    CitationAgent and FactCheckerAgent (via the assembled report) and produces
    a concise, professional summary written for a judge reviewing the motion.

    The memo is strictly synthesizing — it does NOT discover new issues. It only
    summarizes findings that are already present in the report with definitive
    status (flagged or contradicted), ordered by severity.
    """

    def run(self, report: dict) -> str:
        """
        Args:
            report: The assembled report dict from ReportBuilder, containing
                    citation_analysis and fact_analysis.

        Returns:
            A one-paragraph string suitable for inclusion in a judicial memo.
        """
        citations = report.get("citation_analysis", {}).get("citations", [])
        issues = report.get("fact_analysis", {}).get("issues", [])
        summary_stats = report.get("summary_stats", {})

        # Build a compact summary of definitive findings to pass to the LLM
        flagged_citations = [
            {
                "citation": c.get("citation"),
                "proposition": c.get("proposition"),
                "explanation": c.get("explanation"),
            }
            for c in citations
            if c.get("is_citation_real") is False
            or c.get("is_proposition_supported") is False
            or c.get("is_quote_accurate") is False
        ]

        contradicted_facts = [
            {
                "claim": i.get("claim"),
                "status": i.get("status"),
                "evidence": i.get("evidence"),
                "confidence": i.get("confidence"),
            }
            for i in issues
            if i.get("status") in ("contradicted", "unsupported")
        ]

        findings_summary = json.dumps(
            {
                "flagged_citations": flagged_citations,
                "contradicted_facts": contradicted_facts,
                "summary_stats": summary_stats,
            },
            indent=2,
        )

        response = call_llm(
            [
                {
                    "role": "system",
                    "content": """You are a judicial law clerk preparing a bench memo for a judge.

You have been given a structured verification report on a Motion for Summary Judgment
(Rivera v. Harmon Construction Group). The report was produced by an automated AI
pipeline that checked citations and cross-referenced factual claims against the
police report, medical records, and witness statement.

Write a single paragraph (4–6 sentences) summarizing the most material findings for
the judge. The memo should:
  - Identify the most serious issues (fabricated or misrepresented citations, factual
    contradictions with supporting documents) in plain legal prose.
  - State concisely what was wrong and why it matters to the motion.
  - Not introduce any findings not present in the report.
  - Sound like a professional legal memo, not a bullet-point list.
  - End with a sentence noting that the pipeline abstained on any items it could not
    independently verify, and flagged only findings with supporting evidence.

Return ONLY the paragraph text. Do not add headers, bullets, or JSON wrapping.""",
                },
                {
                    "role": "user",
                    "content": f"VERIFICATION REPORT FINDINGS:\n{findings_summary}",
                },
            ]
        )

        return _extract_text(response)
