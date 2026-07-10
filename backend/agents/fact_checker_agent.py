import json
import re
from llm import call_llm


def _extract_json(text: str) -> dict:
    """Extract a JSON object from an LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


class FactCheckerAgent:
    def run(
        self,
        motion: str,
        police_report: str,
        medical_records: str,
        witness_statement: str,
        citations: list = None,
    ) -> dict:
        citations_str = json.dumps(citations or [], indent=2)

        response = call_llm(
            [
                {
                    "role": "system",
                    "content": """You are a legal fact verification agent.

Compare the factual assertions in the motion (and any facts/propositions referenced in the extracted citations)
against the factual record in the supporting documents (police report, medical records, and witness statement).

Your goal is to identify:
1. Contradictions: Assertions in the motion that are directly contradicted by the facts in the other documents.
2. Unsupported claims: Claims in the motion that have no supporting evidence in the other documents.
3. Honest abstention: If the supporting documents do not contain enough information to confirm or refute a claim,
   set status to "could_not_verify" — never fabricate or invent a contradiction. An honest "could not verify"
   is ALWAYS preferable to a confident but unsubstantiated finding.

Status values:
  - "contradicted"      — The claim is directly contradicted by at least one supporting document.
  - "unsupported"       — The claim is not contradicted, but has no corroborating evidence in the documents.
  - "could_not_verify"  — The supporting documents do not contain enough information to confirm or deny the claim.

Return the results in a structured JSON object:
{
  "issues": [
    {
      "claim": "The exact factual assertion from the motion being verified",
      "status": "contradicted|unsupported|could_not_verify",
      "evidence": "Contradicting or missing evidence details, referencing the specific source document (e.g., police report, medical records, witness statement). If could_not_verify, state exactly what information is missing.",
      "confidence": 0.0 to 1.0 confidence score of your finding,
      "explanation": "Brief reasoning explaining the contradiction, lack of support, or why verification was not possible."
    }
  ]
}""",
                },
                {
                    "role": "user",
                    "content": f"""MOTION:
{motion}

EXTRACTED CITATIONS (STRUCTURED):
{citations_str}

POLICE REPORT:
{police_report}

MEDICAL RECORDS:
{medical_records}

WITNESS STATEMENT:
{witness_statement}""",
                },
            ]
        )

        return _extract_json(response)
