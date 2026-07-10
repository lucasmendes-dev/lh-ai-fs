# BS Detector: Design Decisions and Tradeoffs Reflection

This document reflects on the architectural design decisions, agent decomposition, and tradeoffs made during the implementation of the BS Detector legal verification pipeline.

---

## 1. Agent Decomposition & Separation of Concerns

I decomposed the pipeline into four distinct agents rather than one monolithic prompt:

1. **CitationAgent**: Parses legal text, extracts references, checks quote precision, and assesses authority support.
2. **FactCheckerAgent**: Cross-references factual claims in the brief against the police report, medical records, and witness statement. Receives structured citation output from CitationAgent so it can specifically check whether the facts asserted in citation *propositions* are supported by the record.
3. **ReportBuilder**: Aggregates agent outputs into a structured report with summary statistics, confidence aggregation, and a risk level (HIGH/MEDIUM/LOW).
4. **JudicialMemoAgent**: Synthesizes a one-paragraph judicial memo from the finalized report — strictly summarizing findings already present, not discovering new ones.

### Why this approach?
* **Reduced prompt complexity**: Combining citation checking and cross-document fact checking in one prompt leads to context overflow and degrades accuracy. Focused prompts outperform general ones.
* **Granular observability**: If citation checking hallucinates, the error is localized to `CitationAgent` without having to debug the rest of the pipeline.
* **Model substitution**: In production, each agent can be run on a different model tier. CitationAgent benefits from a reasoning model for quote comparison; FactCheckerAgent needs broad context retention. Separation enables that.

---

## 2. Structured Data Passing Between Agents

A key requirement is passing structured data, not raw text blobs, between agents.

* **Implementation**: CitationAgent returns a typed JSON schema (`citation`, `proposition`, `quote`, `is_citation_real`, etc.). This JSON is parsed and passed directly as the `citations` argument to `FactCheckerAgent.run()`.
* **Value**: FactCheckerAgent can check not only the raw motion text, but specifically whether the facts embedded in each citation proposition are corroborated by the supporting documents. For example: if a citation proposition asserts that OSHA compliance establishes reasonable care, the fact checker can cross-reference whether the record documents actually show the claimed level of compliance.

---

## 3. Prompt Engineering Decisions

* **System/User split**: System prompts define role, evaluation rules, and output schema. User prompts supply the actual documents. This separation makes prompt versions diff-friendly and prevents role confusion.
* **Anti-hallucination instruction**: Both agents are explicitly instructed to emit `"could_not_verify"` when evidence is insufficient. This is enforced at the schema level (the output spec allows `true | false | "could_not_verify"`), making non-compliance structurally visible.
* **Confidence scoring**: FactCheckerAgent is prompted to include a 0–1 confidence score per finding. This is used by ReportBuilder to compute aggregate risk level and by the UI to render confidence bars.

---

## 4. Eval Design: Honest Assessment

The evaluation harness (`run_evals.py`) uses keyword-based ground-truth matching, which has known limitations I want to be explicit about.

### What it does well
* **Transparent and reproducible**: The keyword sets are readable and deterministic. Anyone can inspect exactly what the eval is checking.
* **Penalizes hallucination correctly**: A definitive flag on a citation not in ground truth is counted as a false positive.
* **Treats abstention honestly**: `"could_not_verify"` is not penalized as a hallucination — it is recorded separately. Honest uncertainty is better than confident fabrication.

### Known weaknesses
* **Keyword precision limits**: The PPE contradiction required specific keywords (`"personal protective equipment"`, `"fall-arrest"`, `"harness"`) because the claim text doesn't use the word "ppe" alone. I tightened these after noticing the original keyword set missed it. This manual tuning process is fragile: it works for this document, but a real eval suite would use embedding similarity or span-level matching instead.
* **No span-level verification**: The eval checks whether the *claim text* matches a keyword, not whether the *evidence cited* is correct. A response that says the right thing but cites the wrong document would still pass. Production eval would check that the evidence passage actually contains the contradiction.

### What I would do differently
If I were redesigning the eval with more time:
1. **Add span-level matching**: Store (page, char_offset) for each evidence claim. The eval checks whether the cited page actually contains the stated contradiction — much harder to game.
2. **Adversarial test cases**: Add clean citations (no flaws) and confirmed clean facts. Measure that the pipeline does NOT flag them. Right now the eval only checks recall; it does not rigorously test precision on truly clean inputs.
3. **Eval dataset versioning**: The current ground truth is hardcoded in `run_evals.py`. It should be a versioned JSON file checked into source control, so that prompt changes can be compared against historical baselines.

---

## 5. Key Tradeoffs

* **Sequential vs. parallel agent execution**: FactCheckerAgent runs after CitationAgent because it consumes the structured citation list. This serializes the pipeline. In production, CitationAgent output could be streamed to FactCheckerAgent as citations are extracted (via a task queue), cutting end-to-end latency. The sequential approach was chosen for clarity in the prototype.
* **Synchronous API vs. async queue**: The `/analyze` endpoint runs agents synchronously inside the request. For a real LLM backend with 2–10 minute runtimes, this would timeout any HTTP client. Production uses Temporal with a job-polling or WebSocket notification model (see `docs/production-readiness.md`).

---

## 6. Time Spent

Approximately 7–8 hours total:
* ~3.5h: Backend agents, pipeline, eval harness, prompt engineering
* ~1.5h: Frontend UI (structured from raw JSON to cards, badges, confidence bars, judicial memo section)
* ~2h: Production readiness plan and reflection document

The implementation intentionally prioritized eval rigor and honest abstention posture over completeness of Tier 3 features. The gaps I am most aware of: real LLM citation database integration, span-level evidence tracking, and the gameable eval (documented above).
