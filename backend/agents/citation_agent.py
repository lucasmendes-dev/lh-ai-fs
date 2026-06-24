import json
from llm import call_llm

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

Return the results in a structured JSON object:
{
  "citations": [
    {
      "citation": "Full case citation, e.g., Privette v. Superior Court, 5 Cal.4th 689 (1993)",
      "proposition": "The legal proposition or claim supported by this citation",
      "quote": "The direct quote being checked, or null if none",
      "is_quote_accurate": true|false|null,
      "is_citation_real": true|false,
      "is_proposition_supported": true|false,
      "explanation": "Detailed explanation of the support assessment and quote validation"
    }
  ]
}"""
                },
                {
                    "role": "user",
                    "content": motion_text
                }
            ]
        )
        return json.loads(response)
