"""
Thin wrapper around the Anthropic SDK that:
  1. Enforces the budget before each call
  2. Records actual token usage after each call
  3. Routes between Haiku (default) and Sonnet (agent work)
"""
from __future__ import annotations
from typing import Iterable

from anthropic import Anthropic
import structlog

from spend import SpendTracker, BudgetExceeded

log = structlog.get_logger()


class ClaudeClient:
    def __init__(self, api_key: str, config: dict, spend: SpendTracker):
        self.client = Anthropic(api_key=api_key)
        self.config = config
        self.spend = spend

    def _estimate_cost(self, model: str, input_tokens: int, max_output: int) -> float:
        from spend import PRICING
        rates = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        return (input_tokens / 1_000_000) * rates["input"] + \
               (max_output / 1_000_000) * rates["output"]

    def pick_model(self, needs_tools: bool, user_text: str) -> str:
        """Route between Haiku and Sonnet.

        Haiku for: conversational, quick Q&A, simple chit-chat.
        Sonnet for: anything with tool use, multi-step reasoning, or longer context.
        """
        if needs_tools:
            return self.config["models"]["agent"]
        # Heuristic: short prompts stay on Haiku
        if len(user_text) < 200:
            return self.config["models"]["default"]
        return self.config["models"]["agent"]

    def chat(self, messages: list, system: str, tools: list | None = None,
             model: str | None = None, max_tokens: int = 1024) -> dict:
        model = model or self.config["models"]["default"]

        # Rough input estimate: ~4 chars per token
        input_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
        input_estimate += len(system) // 4
        projected = self._estimate_cost(model, input_estimate, max_tokens)
        self.spend.check_budget(projected)

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        # Record actual usage
        usage = response.usage
        self.spend.record_llm_call(
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

        return response
