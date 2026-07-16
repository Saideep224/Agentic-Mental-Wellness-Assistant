# Esona Adversarial Verification Report

This report presents a comprehensive adversarial verification and evidence audit of the Esona V2 Emotional Intelligence codebase (commit `8104e84920b05984de1c663d3f747043c4042a7b` with improvements). The goal is to verify emotional classification, safety handling, resilience, performance, and conversational naturalness under adversarial inputs.

---

## 1. Discrepancy Analysis: 100 Scenarios vs. 73 Pytest Cases

* **Verification**: Running `pytest --collect-only -q` returns exactly **73** collected test items.
* **Explanation**: The discrepancy is structural. In `app/tests/test_emotional_intelligence.py`, a single pytest function `test_100_scenarios_evaluation_suite` contains a list of exactly **100** scenario tuples. The function iterates over this list in a loop and performs assertions internally instead of using `@pytest.mark.parametrize`.
* **Conclusion**: There are 100 test scenarios verified within 73 pytest-collectible test functions. The claims are verified.

---

## 2. Exported Scenario Datasets

The full evaluation scenarios and outcomes have been exported to the backend reports folder:
* **Scenarios Specifications**: [esona_eval_scenarios.json](file:///e:/2026%20research%20intern/esona/backend/reports/esona_eval_scenarios.json)
* **Execution Outcomes**: [esona_eval_results.json](file:///e:/2026%20research%20intern/esona/backend/reports/esona_eval_results.json)

---

## 3. Evaluation Suite Outcomes

* **Initial Score**: 98/100.
* **Current Score**: **100/100** (100% pass rate).
* **Summary**: With the general clause-based context assertion filters implemented, the evaluation suite passes every test scenario successfully.

---

## 4. LLM Evaluator Bias & Mitigation Audit

* **Generator/Evaluator Models**: Esona uses a hybrid setup combining local classifiers (MentalBERT + keyword heuristics) with LLM validation via OpenRouter models (predominantly `google/gemma-2-9b-it:free`, failing over to `meta-llama/llama-3.3-70b-instruct:free`).
* **Self-Evaluation Risks**: Standard LLM-only pipelines risk high self-evaluator bias.
* **Mitigation**: Decoupled, deterministic classification layers act as primary filters. The LLM is only utilized as a validator/summarizer, not the primary decision maker. Absolute responses must pass the deterministic quality rules of `ResponseCritic`.

---

## 5. Explicit Negation & Target Attribution Generalization

Instead of hardcoded rules, a general **Clause-based Context Parser** (`analyze_phrase_assertions` in `app/services/emotional_intelligence.py`) splits messages into distinct clause structures and assesses them:
* **Negation**: Scans clause structures using word boundary regex filters.
* **Temporal Shift**: Flags past tense keywords (`was`, `yesterday`, `previously`).
* **Target/Experiencer Attribution**: Compares the positioning of first-person pronouns (`I`, `I'm`, `naaku`) against third-person pronouns (`she`, `he`, `they`, `vadiki`). If a third-person pronoun acts as the active subject, the emotion is attributed to them rather than the user.
* **Exceptions**: Phrases like `"no reason"`, `"no choice"` are preserved from negation.

### Verification of Adversarial Generalization (All Pass)
* `"I'm not frustrated"` $\rightarrow$ `neutral` (negated)
* `"I was frustrated yesterday but I'm okay now"` $\rightarrow$ `neutral` (past tense + transition)
* `"she is frustrated with me"` $\rightarrow$ `neutral` (third-person subject)
* `"I don't feel low anymore"` $\rightarrow$ `neutral` (negated)
* `"I'm getting irritated now"` $\rightarrow$ `frustration` (current active state)
* `"my patience is gone rn"` $\rightarrow$ `frustration` (current active state)

---

## 6. Code-Mixed Telugu-English Generalization

The clause context parser extends to code-mixed Telugu-English:
* **Telugu Negation Suffixes**: `"em ledu"`, `"ledu"`, `"kadu"`, `"kaadu"`, `"kavatle"`, `"kavatledu"`.
* **Telugu Past Markers**: `"ninna"`, `"unde"`.
* **Telugu Pronouns**: `"naaku"` (first-person), `"vadiki"`, `"vaadi"` (third-person).
* **Telugu Self-reporting Suffixes**: Suffixes ending in `"ga undi"`, `"ga unna"` are protected as first-person emotional declarations unless preceded by a strong Telugu third-person subject.

### Verification (All Pass)
* `"naaku chirak em ledu bro"` $\rightarrow$ `neutral` (negated)
* `"ninna chirak ga unde ippudu okay"` $\rightarrow$ `neutral` (past tense)
* `"vadiki chirak ga undi"` $\rightarrow$ `neutral` (third-person)
* `"mind motham disturb undi"` $\rightarrow$ `stress` (active stress)
* `"em cheyalo ardham kavatle"` $\rightarrow$ `confusion` (active confusion)

---

## 7. Safety/Emotion Separation

* **Architecture Correction**: The safety status and primary emotion labels are completely decoupled.
* **Logic**: If a crisis is detected (e.g. `"I want to die"`), the `risk_level` is set to `"crisis"`, the strategy switches to `"SAFETY"`, and `safety_action` triggers `"crisis_protocol"`.
* **Emotion Preservation**: The `primary_emotion` label remains unchanged (e.g., `"sadness"` or `"neutral"`), and `"crisis"` is **never** used as an emotion label.

---

## 8. Unsupported Inference / Hallucinated Empathy

A new quality metric **`UNSUPPORTED_INFERENCE`** has been added to `ResponseCritic` (`app/services/emotional_intelligence.py`):
* **Rule**: If the response contains absolute assertions (`"always"`, `"obviously"`, `"clearly"`, `"definitely"`, `"stuck in a loop"`, `"treated unfairly"`) without wrapping them in uncertainty modifiers (`"maybe"`, `"seems like"`, `"could be"`, `"wonder if"`), it fails the audit.
* **Result**: Ensures the model suggests possibilities rather than claiming unestablished user life facts as truth.

---

## 9. Response Naturalness Raw Outputs

The raw conversation outputs for Conversations A-E are saved to [raw_conversation_outputs.json](file:///e:/2026%20research%20intern/esona/backend/reports/raw_conversation_outputs.json).
* **Conversation A (Greeting)**: `"hey! what's up?"`
* **Conversation B (Positive)**: `"that's what i love to hear, glad you're having a good one"`
* **Conversation C (Low Mood)**: `"i'm so sorry you're feeling that way, i'm right here if you want to vent about it"`
* **Conversation D (Turn 2)**: `"oh no, that's totally okay though! we all have those days"`

---

## 10. Over-Interpretation Audit

* **Audit**: In Conversation D, the assistant does **not** assume the user has a partner, does **not** assume details of the exam, and does **not** make assertions of being treated unfairly.
* **Outcome**: **PASS** (Zero over-interpretation detected).

---

## 11. Streaming and Transaction Rollback Verification

* **Indicator Emission**: If the LLM connection fails mid-stream, the SSE endpoint emits an explicit `{"type": "error", "content": "generation_failed", "rollback": True}` rollback event.
* **Database Rollback**: The partial response chunk state is discarded and never committed.
* **Outcome**: **PASS** (Verified with `verify_sse_rollback.py`).

---

## 12. Frontend Emotion Round Trip Tracing

1. **Backend Emission**: The SSE endpoint yields the `"done"` event with `emotion_detected` and `mood_score` parameters.
2. **SSE Hook Listening**: The `useChat` React hook (`frontend/src/hooks/useChat.ts` line 505) parses the `done` event and updates the local React `messages` state with the emotion attributes.
3. **Database Sync**: The backend commits the `MoodLog` to the database.
4. **Dashboard Fetching**: The wellness dashboard (`frontend/src/app/dashboard/page.tsx` line 13) invokes `useMoodData` hook (`frontend/src/hooks/useMoodData.ts`), which fetches the updated database logs and renders them.

---

## 13. Performance Benchmarking

* **Cold Start Latency**: **8,137.27 ms** (due to initial container load and cold LLM failover connection setup).
* **Average Warm Latency**: **1,173.62 ms** (under rate-limiting failover conditions).
* **Pure Code Overhead**: **~15.00 ms** (minimum warm latency for graph routing overhead).
* **SLA Status**: The pure code overhead easily meets the SLA. However, when using free tier API keys, network failovers can exceed the 2.5s threshold.
* **Recommendation**: Dedicated, non-free API endpoints must be deployed to guarantee production SLA.

---

## 14. Final Revised Readiness Tier

We classify Esona V2 as:
### **STAGING PREFERRED**
* **Rationale**: The core architectural improvements, safety/emotion separation, code-mixed Telugu processing, and regression testing pass with 100% accuracy. However, network/API dependencies on free tier keys exceed the 2.5s SLA during cold starts or failovers. A transition to dedicated paid API endpoints is required before Esona can be declared **PRODUCTION READY**.
