import json
import re
from llm import call_llm


def _extract_json(text: str) -> dict:
    """Extract a JSON object from an LLM response, stripping markdown fences."""
    # Strip ```json ... ``` or ``` ... ``` fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


class CitationAgent:
    def run(self, motion_text: str) -> dict:
        response = call_llm(
            [
                {
                    "role": "system",
                    "content": """You are a legal citation verification agent.

Analyze the provided motion for summary judgment and do the following:
1. Extract all legal citations (including volume, reporter, page, year) from the main text and footnotes.
2. For each citation, extract the specific proposition/claim it is intended to support in the brief.
3. Identify if a direct quote is cited. If so, return the quote and verify its accuracy against the actual case.
4. Assess whether the cited authority actually supports the legal proposition or claim as stated in the brief.
5. Provide a clear explanation of your findings, highlighting any fabrication, mismatch, or inaccuracy.

IMPORTANT — Anti-hallucination rule:
You do not have access to a legal database. You may have seen some case citations in your training data, but
you cannot reliably confirm whether any specific citation is real or fabricated.
- If you have high confidence that a citation is real and accurately reflects the case law, set is_citation_real to true.
- If you have high confidence that a citation does NOT exist (e.g., parties, volume, page are clearly wrong or the
  quote does not match what the case says), set is_citation_real to false.
- If you are uncertain whether the citation exists or whether the quote/proposition is accurate, set
  is_citation_real to "could_not_verify". A "could_not_verify" answer is ALWAYS preferable to a confident guess.
  Similarly use "could_not_verify" for is_quote_accurate and is_proposition_supported when evidence is insufficient.

Return the results in a structured JSON object:
{
  "citations": [
    {
      "citation": "Full case citation, e.g., Privette v. Superior Court, 5 Cal.4th 689 (1993)",
      "proposition": "The legal proposition or claim supported by this citation",
      "quote": "The direct quote being checked, or null if none",
      "is_quote_accurate": true|false|"could_not_verify"|null,
      "is_citation_real": true|false|"could_not_verify",
      "is_proposition_supported": true|false|"could_not_verify",
      "explanation": "Detailed explanation of the support assessment and quote validation. If could_not_verify, explain why verification was not possible."
    }
  ]
}""",
                },
                {
                    "role": "user",
                    "content": motion_text,
                },
            ]
        )
        return _extract_json(response)
