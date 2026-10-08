"""LLM planner using OpenAI function calling. Used when OPENAI_API_KEY is set."""
import json

from app.agents.context import TurnContext
from app.tools.registry import OPENAI_TOOL_SCHEMAS

SYSTEM_PROMPT = """You are a customer support agent for a SaaS product.
- Use tools to look up facts; never invent account data, charges, or policy.
- Ground policy answers in search_knowledge_base results.
- Before create_support_ticket, tell the customer what you will file and ask for confirmation. The system will hold the ticket until they confirm.
- If the customer asks for a human, is upset, or you cannot resolve the issue, call escalate_to_human.
- Be concise and friendly."""

MAX_STEPS = 5


class OpenAIPlanner:
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def plan(self, ctx: TurnContext, message: str, history: list[dict]) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": message}]
        for _ in range(MAX_STEPS):
            resp = self.client.chat.completions.create(model=self.model, messages=messages, tools=OPENAI_TOOL_SCHEMAS)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content or ""
            messages.append(msg)
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = ctx.run(call.function.name, **args)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        ctx.run("escalate_to_human", reason="Agent exceeded tool-call budget")
        return "I'm having trouble resolving this, so I've handed it to a human agent."
