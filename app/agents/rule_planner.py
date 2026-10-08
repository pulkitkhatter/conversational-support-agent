"""Deterministic planner: keyword intent routing + grounded templated replies.

Runs with no API key, which makes the whole system testable and evaluable offline.
"""
import re

from app.agents.context import TurnContext

_HUMAN = re.compile(r"\b(human|real person|representative|speak to (an? )?agent|talk to (an? )?(agent|person))\b", re.I)
_DOUBLE = re.compile(r"charged (me )?(twice|two times|double)|double[- ]charge|duplicate (charge|payment)|billed twice", re.I)
_BILLING = re.compile(r"\b(charge|charged|billing|bill|invoice|payment|refund)\b", re.I)
_ACCOUNT = re.compile(r"(what|which) plan (am i|do i)|when (does|will) .*renew|\brenewal date\b|account status", re.I)


class RulePlanner:
    def plan(self, ctx: TurnContext, message: str, history: list[dict]) -> str:
        if _HUMAN.search(message):
            ctx.run("escalate_to_human", reason="Customer requested a human agent")
            return "Of course, I'm connecting you with a human agent now. They'll see this conversation so you won't need to repeat yourself."

        if _DOUBLE.search(message):
            return self._double_charge(ctx)

        if _ACCOUNT.search(message):
            sub = ctx.run("get_subscription")
            if sub.get("found"):
                return f"You're on the {sub['plan']} plan (${sub['monthly_price']:.2f}/month), status {sub['status']}. Next renewal: {sub['next_renewal']}."

        return self._answer_from_kb(ctx, message)

    def _double_charge(self, ctx: TurnContext) -> str:
        ctx.run("get_customer_profile")
        sub = ctx.run("get_subscription")
        kb = ctx.run("search_knowledge_base", query="refund policy duplicate charges")
        policy = kb["hits"][0]["text"].split(". ")[0] if kb["hits"] else "Duplicate charges are refunded once verified."
        dupes = sub.get("duplicate_charges", [])
        if not dupes:
            return "I checked your account and didn't find a duplicate charge this month. Would you like me to connect you with a human agent to look closer?"
        ids = " and ".join(dupes[0])
        amount = next(c["amount"] for c in sub["charges"] if c["id"] == dupes[0][0])
        ctx.run("create_support_ticket", subject="Duplicate charge investigation", details=f"Charges {ids} for ${amount:.2f} each")
        return (
            f"I checked your account and found two charges of ${amount:.2f} on the same day ({ids}). "
            f"Per our policy: {policy}. I can create a billing investigation ticket for you. Would you like me to proceed?"
        )

    def _answer_from_kb(self, ctx: TurnContext, message: str) -> str:
        kb = ctx.run("search_knowledge_base", query=message)
        hits = kb["hits"]
        if not hits or hits[0]["score"] < 1.0:
            return "I'm not sure about that one. I can connect you with a human agent if you'd like — just say so."
        top = hits[0]
        return f"{top['text']}\n\n(Source: {top['doc']} / {top['section']})"
