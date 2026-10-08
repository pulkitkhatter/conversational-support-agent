"""Conversation orchestrator: guardrails -> memory -> (confirmation | planner) -> memory."""
import re
import uuid

from app.agents.context import TurnContext
from app.agents.rule_planner import RulePlanner
from app.config import Settings
from app.guardrails.guards import is_injection, redact_pii
from app.memory.store import MemoryStore
from app.rag.retriever import Retriever
from app.schemas import ChatResponse
from app.tools.registry import ToolRegistry

_YES = re.compile(r"^\s*(yes|yep|yeah|sure|ok|okay|please do|go ahead|proceed|confirm)\b", re.I)
_NO = re.compile(r"^\s*(no|nope|don'?t|cancel|stop|never ?mind)\b", re.I)


class Orchestrator:
    def __init__(self, settings: Settings, memory: MemoryStore | None = None, planner=None):
        self.memory = memory or MemoryStore(settings.memory_db_path)
        self.tools = ToolRegistry(Retriever())
        if planner is not None:
            self.planner = planner
        elif settings.openai_api_key:
            from app.agents.openai_planner import OpenAIPlanner

            self.planner = OpenAIPlanner(settings.openai_api_key, settings.openai_model)
        else:
            self.planner = RulePlanner()

    def handle(self, message: str, session_id: str | None, customer_id: str) -> ChatResponse:
        session_id = session_id or uuid.uuid4().hex[:12]
        ctx = TurnContext(self.tools, customer_id)
        state = self.memory.get_state(session_id)
        history = self.memory.history(session_id)

        self.memory.add_message(session_id, "user", redact_pii(message))

        if is_injection(message):
            reply = "I can't help with that request. I can help with billing, account, and support questions."
        elif state.get("escalated"):
            reply = "A human agent already has this conversation and will reply shortly."
            ctx.escalated = True
        elif state.get("pending") and _YES.match(message):
            result = ctx.execute_confirmed(state.pop("pending"))
            reply = f"Done. I created ticket {result['ticket_id']}. The billing team will review it within 2 business days."
        elif state.get("pending") and _NO.match(message):
            state.pop("pending")
            reply = "No problem, I won't create a ticket. Is there anything else I can help with?"
        else:
            state.pop("pending", None)
            reply = self.planner.plan(ctx, message, history)
            if ctx.pending:
                state["pending"] = ctx.pending

        if ctx.escalated:
            state["escalated"] = True
        self.memory.set_state(session_id, state)
        self.memory.add_message(session_id, "assistant", reply)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            tool_calls=ctx.calls,
            sources=ctx.sources,
            escalated=bool(state.get("escalated")),
            awaiting_confirmation="pending" in state,
        )
