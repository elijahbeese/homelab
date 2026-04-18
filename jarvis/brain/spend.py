"""
Spend guardrail — tracks cumulative API cost and refuses calls past the cap.

Stores a JSON ledger at /app/state/spend.json so restarts don't wipe tracking.
Prices are hardcoded based on published rates and can be updated in PRICING.
"""
from __future__ import annotations
import json
import os
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger()

# Per-million-token pricing in USD. Keep this in sync with
# https://platform.claude.com/docs/en/about-claude/pricing
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
    "claude-opus-4-7":           {"input": 5.00, "output": 25.00},
    # Fallback — if model isn't listed, use Sonnet pricing (conservative)
}
WEB_SEARCH_PER_CALL = 0.01  # $10 / 1000 searches


class BudgetExceeded(Exception):
    """Raised when a spend limit would be exceeded by the next call."""


class SpendTracker:
    def __init__(self, state_path: Path, daily_limit: float,
                 monthly_limit: float, web_search_daily_limit: int):
        self.state_path = state_path
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.web_search_daily_limit = web_search_daily_limit
        self._lock = threading.Lock()
        self._state = self._load()

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except Exception as e:
                log.warning("spend_state_unreadable_resetting", error=str(e))
        return {
            "daily": {},    # "YYYY-MM-DD" -> {"usd": float, "web_searches": int}
            "monthly": {},  # "YYYY-MM"   -> {"usd": float}
        }

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2))
        tmp.replace(self.state_path)

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _month_key(self) -> str:
        return date.today().strftime("%Y-%m")

    def _ensure_buckets(self) -> tuple[dict, dict]:
        d = self._state["daily"].setdefault(self._today_key(), {"usd": 0.0, "web_searches": 0})
        m = self._state["monthly"].setdefault(self._month_key(), {"usd": 0.0})
        return d, m

    def check_budget(self, projected_cost_usd: float = 0.0) -> None:
        """Raises BudgetExceeded if the next call would blow the cap."""
        with self._lock:
            d, m = self._ensure_buckets()
            if d["usd"] + projected_cost_usd > self.daily_limit:
                raise BudgetExceeded(
                    f"Daily budget ${self.daily_limit:.2f} would be exceeded "
                    f"(spent ${d['usd']:.4f}, projected +${projected_cost_usd:.4f})"
                )
            if m["usd"] + projected_cost_usd > self.monthly_limit:
                raise BudgetExceeded(
                    f"Monthly budget ${self.monthly_limit:.2f} would be exceeded "
                    f"(spent ${m['usd']:.4f}, projected +${projected_cost_usd:.4f})"
                )

    def check_web_search(self) -> None:
        with self._lock:
            d, _ = self._ensure_buckets()
            if d["web_searches"] >= self.web_search_daily_limit:
                raise BudgetExceeded(
                    f"Daily web search limit ({self.web_search_daily_limit}) hit"
                )

    def record_llm_call(self, model: str, input_tokens: int, output_tokens: int,
                        cache_read_tokens: int = 0,
                        cache_write_tokens: int = 0) -> float:
        """Record actual token usage and return USD cost."""
        rates = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        cost = (
            (input_tokens / 1_000_000) * rates["input"]
            + (output_tokens / 1_000_000) * rates["output"]
            + (cache_read_tokens / 1_000_000) * (rates["input"] * 0.10)
            + (cache_write_tokens / 1_000_000) * (rates["input"] * 1.25)
        )
        with self._lock:
            d, m = self._ensure_buckets()
            d["usd"] += cost
            m["usd"] += cost
            self._save()
        log.info("llm_call_recorded", model=model, cost_usd=round(cost, 6),
                 daily_total=round(d["usd"], 4),
                 monthly_total=round(m["usd"], 4))
        return cost

    def record_web_search(self, count: int = 1) -> float:
        cost = count * WEB_SEARCH_PER_CALL
        with self._lock:
            d, m = self._ensure_buckets()
            d["usd"] += cost
            d["web_searches"] += count
            m["usd"] += cost
            self._save()
        return cost

    def status(self) -> dict:
        """Human-readable spend summary."""
        with self._lock:
            d, m = self._ensure_buckets()
            return {
                "daily": {
                    "spent_usd": round(d["usd"], 4),
                    "limit_usd": self.daily_limit,
                    "remaining_usd": round(self.daily_limit - d["usd"], 4),
                    "web_searches": d["web_searches"],
                    "web_search_limit": self.web_search_daily_limit,
                },
                "monthly": {
                    "spent_usd": round(m["usd"], 4),
                    "limit_usd": self.monthly_limit,
                    "remaining_usd": round(self.monthly_limit - m["usd"], 4),
                },
            }


def build_from_config(cfg: dict) -> SpendTracker:
    state_path = Path(os.environ.get("JARVIS_STATE_DIR", "/app/state")) / "spend.json"
    b = cfg["budget"]
    return SpendTracker(
        state_path=state_path,
        daily_limit=b["daily_usd_limit"],
        monthly_limit=b["monthly_usd_limit"],
        web_search_daily_limit=b["web_search_daily_limit"],
    )
