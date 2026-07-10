class ReportBuilder:
    """Assembles the full verification report from agent outputs.

    Beyond simply merging the two agent outputs, this builder computes:
      - summary_stats: aggregate counts of issues by type and severity, plus
        abstention rate and overall risk level.
      - risk_level: HIGH / MEDIUM / LOW based on definitive finding count.

    The risk_level and summary_stats are consumed by both the frontend UI
    (for dashboard display) and the JudicialMemoAgent (for context).
    """

    def build(
        self,
        citation_analysis: dict,
        fact_analysis: dict,
    ) -> dict:
        citations = citation_analysis.get("citations", [])
        issues = fact_analysis.get("issues", [])

        # Citation counts
        citation_definitive_flags = sum(
            1 for c in citations
            if c.get("is_citation_real") is False
            or c.get("is_proposition_supported") is False
            or c.get("is_quote_accurate") is False
        )
        citation_abstentions = sum(
            1 for c in citations
            if (
                c.get("is_citation_real") == "could_not_verify"
                or c.get("is_proposition_supported") == "could_not_verify"
                or c.get("is_quote_accurate") == "could_not_verify"
            ) and not (
                c.get("is_citation_real") is False
                or c.get("is_proposition_supported") is False
                or c.get("is_quote_accurate") is False
            )
        )
        citation_verified = len(citations) - citation_definitive_flags - citation_abstentions

        # Fact counts
        fact_contradicted = sum(1 for i in issues if i.get("status") == "contradicted")
        fact_unsupported = sum(1 for i in issues if i.get("status") == "unsupported")
        fact_abstained = sum(1 for i in issues if i.get("status") == "could_not_verify")

        total_definitive = citation_definitive_flags + fact_contradicted + fact_unsupported
        total_examined = len(citations) + len(issues)
        abstention_rate = (
            (citation_abstentions + fact_abstained) / total_examined
            if total_examined > 0 else 0.0
        )

        # Aggregate confidence across definitive fact findings
        definitive_issues = [i for i in issues if i.get("status") in ("contradicted", "unsupported")]
        avg_confidence = (
            sum(i.get("confidence", 0.0) for i in definitive_issues) / len(definitive_issues)
            if definitive_issues else 0.0
        )

        # Risk level: based on number of definitive findings with high confidence
        high_confidence_flags = sum(
            1 for i in definitive_issues if i.get("confidence", 0) >= 0.9
        ) + citation_definitive_flags  # citations don't have confidence scores

        if high_confidence_flags >= 4:
            risk_level = "HIGH"
        elif high_confidence_flags >= 2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        summary_stats = {
            "total_citations_examined": len(citations),
            "citation_definitive_flags": citation_definitive_flags,
            "citation_abstentions": citation_abstentions,
            "citation_verified_clean": citation_verified,
            "total_fact_claims_examined": len(issues),
            "fact_contradicted": fact_contradicted,
            "fact_unsupported": fact_unsupported,
            "fact_abstained": fact_abstained,
            "total_definitive_findings": total_definitive,
            "abstention_rate": round(abstention_rate, 3),
            "avg_fact_confidence": round(avg_confidence, 3),
            "risk_level": risk_level,
        }

        return {
            "summary_stats": summary_stats,
            "risk_level": risk_level,
            "citation_analysis": citation_analysis,
            "fact_analysis": fact_analysis,
        }
