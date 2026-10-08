# production-ai-support-agent

Production-grade conversational AI agent with RAG, tool calling, persistent memory, human escalation, evaluations, and FastAPI.

## What problem does this solve?
Support chatbots that just forward text to an LLM hallucinate account data and take actions nobody approved. This agent looks facts up through tools, grounds policy answers in a knowledge base with citations, asks before it acts, and hands off to a human when it should.

```
User -> FastAPI -> Orchestrator -> Guardrails (injection screen, PII redaction)
                       |-> Memory   (SQLite: history + session state)
                       |-> Planner  (OpenAI function calling | deterministic rule planner)
                       |-> Tools    (KB search, profile, subscription, ticket, escalate)
                       '-> RAG      (BM25 over markdown KB, section-level chunks, cited)
```

## Key capabilities
- **Multi-turn memory** persisted in SQLite (`MEMORY_DB_PATH`), including per-session state (pending confirmation, escalation).
- **Tool calling** with 5 tools; `customer_id` is injected server-side, never chosen by the model.
- **Human-in-the-loop**: `create_support_ticket` is held until the customer says yes. Enforced in code (`TurnContext.run`), not in the prompt, so it holds for any LLM.
- **RAG with citations**: each answer returns the `sources` it used.
- **Human escalation**: sticky per session, priority queue for priority-tier customers.
- **Guardrails**: prompt-injection screening; card/SSN/email redaction before anything is stored.
- **Runs offline**: with no `OPENAI_API_KEY` a deterministic planner is used, so tests and evals need no network or spend.

## Example
```
POST /chat {"message": "I was charged twice this month.", "customer_id": "cus_1001"}
-> tool_calls: get_customer_profile, get_subscription, search_knowledge_base, create_support_ticket(pending)
-> "I checked your account and found two charges of $49.00 on the same day (ch_9001 and ch_9002). ...
    Would you like me to proceed?"
POST /chat {"message": "yes please", "session_id": "..."}
-> "Done. I created ticket TCK-1001. ..."
```

## Run it
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optionally add OPENAI_API_KEY
uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
```
Docker: `docker compose up --build`

## Tests and evaluation
```bash
pytest -q                 # 17 passed
python -m evals.run_evals # writes evals/results.json
```
Last local run of the eval harness (12 hand-written cases in `evals/dataset.jsonl`, rule-based planner):

| Metric | Result |
|---|---|
| Tool selection accuracy | 12/12 |
| Retrieval correctness (top-1 source) | 9/9 where a source is expected |
| Task completion (ticket created iff expected) | 12/12 |

**Read these honestly:** the dataset is small, written by the author alongside the rule planner, so it is a regression suite, not a benchmark. The OpenAI planner is implemented but has not been evaluated; grow the dataset and run it with a key before quoting numbers for that mode.

## Engineering decisions
- **Confirmation gate in code, not prompt.** Prompts are suggestions; side effects need enforcement.
- **Planner interface.** Rule and LLM planners share `plan(ctx, message, history)`, so orchestration, safety, and memory are tested once.
- **BM25 first.** Zero-dependency, explainable, good enough for a small KB. `Retriever.search()` is the seam for pgvector/FAISS embeddings.
- **SQLite for memory** keeps it runnable anywhere; the `MemoryStore` methods map directly onto Postgres.

## Layout
```
app/agents      orchestrator, rule + OpenAI planners, turn context
app/tools       tool registry + OpenAI schemas (mock customer data)
app/rag         BM25 retriever + kb/*.md
app/memory      SQLite store
app/guardrails  injection + PII
app/api         /health, /chat
tests/  evals/  .github/workflows/tests.yml
```

## Roadmap
Embedding retriever (pgvector), Redis rate limiting, OpenTelemetry tracing, LangGraph port of the orchestrator, Gradio demo on Hugging Face Spaces, architecture diagram in `docs/`.

## License
MIT
