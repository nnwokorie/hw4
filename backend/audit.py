"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One record per chat run: when it happened, who (user id or guest, never email/password), which page,
each model step and tool call (short args + short result), fact-check retries, and why the run stopped.
The file is a JSON array that only ever grows: each write re-reads the existing records, appends,
and atomically replaces the file under a lock. Nothing is ever deleted between runs or restarts.
"""

import fcntl
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_LOCK = threading.Lock()
MAX = 200  # characters kept for args / results


# Card-like numbers (13-19 digits, optional spaces/dashes), SSN-style IDs, and "password: ..." phrases.
_SENSITIVE = [
    (re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), "[REDACTED NUMBER]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED ID]"),
    (re.compile(r"(?i)\b(password|passcode|pwd)\b\s*(?:is|:|=)?\s*\S+"), r"\1 [REDACTED]"),
]


def redact(text: str) -> str:
    """Mask sensitive data before it is written anywhere (audit trail, saved chat history)."""
    for rx, repl in _SENSITIVE:
        text = rx.sub(repl, text)
    return text


def _clip(text: str, n: int = MAX) -> str:
    text = redact(" ".join(str(text).split()))
    return text if len(text) <= n else text[: n - 1] + "…"


def _ts(dt: datetime | None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _summarize_result(content: Any) -> str:
    """Short, human-readable tool result (counts, names, prices), not the full payload."""
    if isinstance(content, BaseModel):
        d = content.model_dump()
        if "error" in d:
            return _clip(f"ERROR: {d['error']}")
        if "message" in d:  # StockResult
            return _clip(d["message"])
        if "total_matches" in d:  # SearchResult
            names = ", ".join(f"{p['name']} (${p['price']:.2f})" for p in d["products"][:3])
            more = f" +{len(d['products']) - 3} more" if len(d["products"]) > 3 else ""
            return _clip(f"{d['total_matches']} matches, returned {len(d['products'])}: {names}{more}")
        if "description" in d and "price" in d:  # ProductInfo
            return _clip(f"{d['name']}: ${d['price']:.2f}, colors {', '.join(d['colors'])}")
        return _clip(json.dumps(d, default=str))
    if isinstance(content, dict) and "logged_in" in content:  # customer profile: don't log email
        return "logged_in=" + str(content["logged_in"])
    return _clip(json.dumps(content, default=str) if isinstance(content, (dict, list)) else content)


def _steps(messages: list[ModelMessage]) -> list[dict]:
    steps: list[dict] = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    args = part.args if isinstance(part.args, str) else json.dumps(part.args or {})
                    if part.tool_name == "final_result":  # structured output (AgentReply)
                        try:
                            out = json.loads(args)
                            n = len((out.get("matches") or {}).get("product_ids", []))
                            args = f"reply={_clip(out.get('reply', ''), 120)!r}, matches={n} product_ids"
                        except ValueError:
                            pass
                    steps.append({"time": _ts(msg.timestamp), "type": "tool_call", "tool": part.tool_name, "args": _clip(args)})
                elif isinstance(part, TextPart) and part.content.strip():
                    steps.append({"time": _ts(msg.timestamp), "type": "model_text", "text": _clip(part.content, 120)})
            if msg.finish_reason:
                steps.append({"time": _ts(msg.timestamp), "type": "model_step_end", "finish_reason": msg.finish_reason})
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    steps.append({"time": _ts(part.timestamp), "type": "tool_result", "tool": part.tool_name,
                                  "result": _summarize_result(part.content)})
                elif isinstance(part, RetryPromptPart):
                    kind = "fact_check_retry" if part.tool_name in (None, "final_result") else "tool_retry"
                    content = part.content if isinstance(part.content, str) else json.dumps(part.content, default=str)
                    steps.append({"time": _ts(part.timestamp), "type": kind, "tool": part.tool_name, "detail": _clip(content)})
    return steps


def log_run(
    *,
    started: datetime,
    user_id: int | None,
    page_path: str,
    viewed_product: str | None,
    message: str,
    messages: list[ModelMessage],
    stop_reason: str,
    model: str,
    usage: dict | None = None,
    reply: str | None = None,
    shown_products: int = 0,
    verified: bool = False,
    error: str | None = None,
) -> None:
    steps = _steps(messages)
    record = {
        "run_id": uuid.uuid4().hex[:12],
        "started_at": _ts(started),
        "ended_at": _ts(None),
        "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        "model": model,
        "user": f"user:{user_id}" if user_id is not None else "guest",
        "page": page_path,
        "viewed_product": viewed_product,
        "message": _clip(message, 300),
        "steps": steps,
        "tool_calls": [s["tool"] for s in steps if s["type"] == "tool_call" and s["tool"] != "final_result"],
        "fact_check_retries": sum(1 for s in steps if s["type"] == "fact_check_retry"),
        "stop_reason": stop_reason,
        "reply": _clip(reply, 300) if reply else None,
        "products_shown": shown_products,
        "verified_badge": verified,
        "usage": usage,
        "error": error,
    }
    append(record)


def append(record: dict) -> None:
    """Append one record. Never truncates: re-reads existing records and atomically replaces the file."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, open(AUDIT_PATH.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records: list = []
        if AUDIT_PATH.exists():
            try:
                records = json.loads(AUDIT_PATH.read_text() or "[]")
            except ValueError:
                # Never overwrite a file we can't parse: keep it aside and start a new one.
                AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{int(datetime.now().timestamp())}.json"))
                records = []
        records.append(record)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False))
        os.replace(tmp, AUDIT_PATH)
