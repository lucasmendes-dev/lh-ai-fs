# BS Detector: Design Decisions and Tradeoffs Reflection

This document reflects on the architectural design decisions, agent decomposition, and tradeoffs made during the implementation of the BS Detector legal verification pipeline.

---

## 1. Agent Decomposition & Separation of Concerns

I decomposed the pipeline into distinct, focused agents rather than utilizing a single monolithic agent:

1. **CitationAgent (Tier 1)**: Focuses exclusively on parsing legal text, identifying references, checking quote precision, and verifying authority support.
2. **FactCheckerAgent (Tier 2)**: Focuses on comparing statements in the brief against external factual files (depositions, police reports, medical documents).
3. **ReportBuilder**: Merges and structures the outputs of both agents.

### Why this approach?
* **Reduced Prompt Complexity**: Combining citation checking and cross-document fact checking in one single LLM prompt leads to context overflow and degrades extraction accuracy. Keeping their prompts separated ensures the models focus on one cognitive task at a time.
* **Granular Observability**: If citation checking fails or hallucinates, we can easily identify that the error occurred in the `CitationAgent` prompt without having to debug the fact-checker logic.
* **Model Suitability**: Citation checking relies heavily on strict string validation and reference matching. Fact checking requires complex reasoning about contradictions and contradictions in time/date sequences. Separating them allows us to run different models for each task in production (e.g., a fast model for citation lookup and a reasoning model for fact matching).

---

## 2. Structured Data Passing Between Agents

A key requirement in Tier 2 is to pass structured data rather than raw text blobs between agents. 
* **Implementation**: I structured the output of `CitationAgent` as a typed JSON schema containing keys for the citation, the proposition, and quote accuracy. This JSON output is parsed by the API coordinator (`main.py`) and passed directly as the `citations` argument to `FactCheckerAgent.run()`.
* **Value Added**: This design allows `FactCheckerAgent` to not only check the raw motion text, but specifically check if the facts asserted in the *citation propositions* are supported by the records. For example, if a citation proposition asserts that a lawsuit was filed timely, the fact checker can check the actual filing date in the complaint against the incident date in the police report.

---

## 3. Prompt Engineering Decisions

I utilized strict JSON schemas in the system prompts for both agents:
* **System/User Message Split**: System prompts are reserved for role definition, evaluation guidelines (e.g., instructions on quote comparison or handling uncertainty), and output JSON schemas. User prompts are used exclusively to supply the actual context documents.
* **Uncertainty Handling**: The `FactCheckerAgent` is explicitly instructed in the system prompt to return `status: "unsupported"` and state `"could not verify"` if the supporting documents contain no evidence to confirm or deny a claim. This prevents the agent from making assumptions or fabricating evidence when documents are missing.

---

## 4. Key Tradeoffs

* **Sequential vs. Parallel Agent Execution**: In our prototype, `FactCheckerAgent` runs sequentially after `CitationAgent` because it consumes the structured citation list. While this introduces minor processing latency compared to running them in parallel, the increase in factual verification accuracy (by cross-checking citation propositions) outweighs the latency tradeoff for legal applications where accuracy is the top priority.
* **Direct REST API vs. Message Queue**: For the prototype, the `/analyze` endpoint executes the agents synchronously within the request context. For production, I would immediately trade this for an asynchronous job queue (Temporal/Celery) as designed in the Production Readiness Plan, to prevent HTTP timeouts.
