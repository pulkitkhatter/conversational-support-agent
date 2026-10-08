"""The five agent tools plus their OpenAI function-calling schemas.

Every tool takes `customer_id` implicitly (injected by the orchestrator, never by
the model) so the LLM cannot read or act on another customer's account.
"""
import itertools
from typing import Callable

from app.rag.retriever import Retriever

CUSTOMERS = {
    "cus_1001": {"name": "Ava Patel", "email": "ava@example.com", "plan": "Pro", "tier": "standard"},
    "cus_1002": {"name": "Liam Chen", "email": "liam@example.com", "plan": "Business", "tier": "priority"},
    "cus_1003": {"name": "Noor Ali", "email": "noor@example.com", "plan": "Starter", "tier": "standard"},
}

SUBSCRIPTIONS = {
    "cus_1001": {
        "plan": "Pro", "status": "active", "monthly_price": 49.0, "next_renewal": "2026-11-01",
        "charges": [
            {"id": "ch_9001", "date": "2026-10-01", "amount": 49.0},
            {"id": "ch_9002", "date": "2026-10-01", "amount": 49.0},
            {"id": "ch_8800", "date": "2026-09-01", "amount": 49.0},
        ],
    },
    "cus_1002": {
        "plan": "Business", "status": "active", "monthly_price": 199.0, "next_renewal": "2026-11-05",
        "charges": [{"id": "ch_7001", "date": "2026-10-05", "amount": 199.0}],
    },
    "cus_1003": {
        "plan": "Starter", "status": "past_due", "monthly_price": 9.0, "next_renewal": "2026-10-20",
        "charges": [{"id": "ch_6001", "date": "2026-09-20", "amount": 9.0}],
    },
}

TICKETS: list[dict] = []
ESCALATIONS: list[dict] = []
_ticket_ids = itertools.count(1001)


class ToolError(Exception):
    pass


class ToolRegistry:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self._tools: dict[str, Callable[..., dict]] = {
            "search_knowledge_base": self.search_knowledge_base,
            "get_customer_profile": self.get_customer_profile,
            "get_subscription": self.get_subscription,
            "create_support_ticket": self.create_support_ticket,
            "escalate_to_human": self.escalate_to_human,
        }

    def call(self, name: str, customer_id: str, **args) -> dict:
        if name not in self._tools:
            raise ToolError(f"unknown tool: {name}")
        return self._tools[name](customer_id=customer_id, **args)

    def search_knowledge_base(self, customer_id: str, query: str) -> dict:
        hits = self.retriever.search(query, k=3)
        return {"hits": [h.__dict__ for h in hits]}

    def get_customer_profile(self, customer_id: str) -> dict:
        profile = CUSTOMERS.get(customer_id)
        if not profile:
            return {"found": False}
        return {"found": True, "customer_id": customer_id, **profile}

    def get_subscription(self, customer_id: str) -> dict:
        sub = SUBSCRIPTIONS.get(customer_id)
        if not sub:
            return {"found": False}
        seen, duplicates = {}, []
        for ch in sub["charges"]:
            key = (ch["date"][:7], ch["amount"])
            if key in seen:
                duplicates.append([seen[key], ch["id"]])
            else:
                seen[key] = ch["id"]
        return {"found": True, **sub, "duplicate_charges": duplicates}

    def create_support_ticket(self, customer_id: str, subject: str, details: str = "") -> dict:
        ticket = {"ticket_id": f"TCK-{next(_ticket_ids)}", "customer_id": customer_id, "subject": subject, "details": details, "status": "open"}
        TICKETS.append(ticket)
        return ticket

    def escalate_to_human(self, customer_id: str, reason: str) -> dict:
        tier = CUSTOMERS.get(customer_id, {}).get("tier", "standard")
        item = {"customer_id": customer_id, "reason": reason, "queue": "priority" if tier == "priority" else "standard"}
        ESCALATIONS.append(item)
        return {"escalated": True, **item}


def _fn(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": required}}}


OPENAI_TOOL_SCHEMAS = [
    _fn("search_knowledge_base", "Search help-center articles (refund policy, billing, account, support hours).", {"query": {"type": "string"}}, ["query"]),
    _fn("get_customer_profile", "Get the current customer's profile.", {}, []),
    _fn("get_subscription", "Get the current customer's plan, status, recent charges and detected duplicate charges.", {}, []),
    _fn("create_support_ticket", "Create a support ticket. Only call after the customer explicitly confirms.", {"subject": {"type": "string"}, "details": {"type": "string"}}, ["subject"]),
    _fn("escalate_to_human", "Hand the conversation to a human agent.", {"reason": {"type": "string"}}, ["reason"]),
]
