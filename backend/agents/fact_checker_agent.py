import json
from llm import call_llm

class FactCheckerAgent:
    def run(
        self,
        motion: str,
        police_report: str,
        medical_records: str,
        witness_statement: str,
        citations: list = None
    ) -> dict:
        citations_str = json.dumps(citations or [], indent=2)

        response = call_llm(
            [
                {
                    "role": "system",
                    "content": """You are a legal fact verification agent.

Compare the factual assertions in the motion (and any facts/propositions referenced in the extracted citations) against the factual record in the supporting documents (police report, medical records, and witness statement).

Your goal is to identify:
1. Contradictions: Assertions in the motion that are directly contradicted by the facts in the other documents.
2. Unsupported claims: Claims in the motion that have no supporting evidence in the other documents.
3. Appropriate uncertainty: If there is insufficient information in the supporting documents to confirm or deny a claim, set its status to 'unsupported' and note that you 'could not verify' it. Do not fabricate findings.

Return the results in a structured JSON object:
{
  "issues": [
    {
      "claim": "The exact factual assertion from the motion being verified",
      "status": "contradicted|unsupported",
      "evidence": "Contradicting or missing evidence details, referencing the specific source document (e.g., police report, medical records, witness statement). If it cannot be verified, state 'could not verify' with details.",
      "confidence": 0.0 to 1.0 confidence score of your finding,
      "explanation": "Brief reasoning explaining the contradiction or lack of support"
    }
  ]
}"""
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
{witness_statement}"""
                }
            ]
        )

        return json.loads(response)
