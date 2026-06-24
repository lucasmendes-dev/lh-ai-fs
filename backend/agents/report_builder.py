class ReportBuilder:
    def build(
        self,
        citation_analysis: dict,
        fact_analysis: dict,
    ) -> dict:

        return {
            "citation_analysis": citation_analysis,
            "fact_analysis": fact_analysis,
        }
