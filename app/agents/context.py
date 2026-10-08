from app.rag.retriever import Hit
from app.schemas import Source, ToolCall
from app.tools.registry import ToolRegistry


class TurnContext:
    """Per-turn execution context. All tool calls go through `run`, which records
    them and enforces the human-in-the-loop gate on ticket creation."""

    def __init__(self, tools: ToolRegistry, customer_id: str):
        self.tools = tools
        self.customer_id = customer_id
        self.calls: list[ToolCall] = []
        self.sources: list[Source] = []
        self.pending: dict | None = None
        self.escalated = False

    def run(self, name: str, **args) -> dict:
        if name == "create_support_ticket":
            self.pending = {"tool": name, "args": args}
            result = {"status": "awaiting_customer_confirmation", **args}
        else:
            result = self.tools.call(name, self.customer_id, **args)
        if name == "escalate_to_human":
            self.escalated = True
        if name == "search_knowledge_base":
            self.sources = [Source(doc=h["doc"], section=h["section"], score=h["score"]) for h in result["hits"]]
        self.calls.append(ToolCall(name=name, args=args, result=_summarize(result)))
        return result

    def execute_confirmed(self, pending: dict) -> dict:
        result = self.tools.call(pending["tool"], self.customer_id, **pending["args"])
        self.calls.append(ToolCall(name=pending["tool"], args=pending["args"], result=result))
        return result


def _summarize(result: dict) -> dict:
    if "hits" in result:
        return {"hits": [f"{h['doc']}/{h['section']} ({h['score']})" for h in result["hits"]]}
    return result
