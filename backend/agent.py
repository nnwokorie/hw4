"""Wires the Campus Customs shop agent: system prompt file + model + tools + structured output."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from datetime import datetime, timezone

from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
from models import AgentReply, ChatResponse, ChatTurn, PageResults, ShopDeps
from tools import SHOP_TOOLS, product_cards

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")  # hw4/.env (copy of .env.example)
load_dotenv(HERE.parent.parent / ".env")  # fallback: course-folder .env one level up (never overrides the above)

PROMPT_PATH = HERE / "prompts" / "prompt.md"
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
USAGE_LIMITS = UsageLimits(request_limit=8)


def make_model() -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Copy .env.example to .env and add your key.")
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": key})
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


shop_agent = Agent(
    make_model(),
    deps_type=ShopDeps,
    output_type=AgentReply,
    instructions=PROMPT_PATH.read_text(),
    tools=SHOP_TOOLS,
    retries=2,  # lets the fact-checker send the model back to fix a reply up to 2 times
)

PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
QTY_RE = re.compile(r"\b(\d+)\b\s*(?:\*\*)?\s*(?:left|in stock|available|remaining|units?)\b", re.I)
QTY_RE_2 = re.compile(r"\b(?:only|just)\s*(?:\*\*)?\s*(\d+)\b", re.I)
COUNT_RE = re.compile(
    r"\b(\d+)\s*(?:\*\*)?\s+(?:[a-z\-]+\s+){0,2}(?:hoodies|hoods|crewnecks|tees|t-shirts|shirts|quarter-zips|jackets|"
    r"items|styles|options|products|pieces|matches|results)\b",
    re.I,
)
SIZE_QTY_RE = re.compile(r"\b(?:XXS|XS|S|M|L|XL|XXL)\b\s*(?:\*\*)?\s*[:\-–]\s*(?:\*\*)?\s*(\d+)\b")


@shop_agent.output_validator
def fact_check(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
    """Every price and stock count in the reply must match a number a tool returned this run
    (or a number the shopper typed, e.g. "under $60"). Otherwise the model must rewrite the reply."""
    deps = ctx.deps
    user_numbers = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", deps.user_message)}
    bad: list[str] = []
    checked = 0
    for m in PRICE_RE.finditer(output.reply):
        value = float(m.group(1))
        checked += 1
        if value not in deps.known_prices and value not in user_numbers:
            bad.append(f"price ${m.group(1)}")
    for rx in (QTY_RE, QTY_RE_2, SIZE_QTY_RE, COUNT_RE):
        for m in rx.finditer(output.reply):
            value = int(m.group(1))
            checked += 1
            if value not in deps.known_quantities and value not in user_numbers:
                bad.append(f"quantity {value}")
    if bad:
        raise ModelRetry(
            "Fact-check failed: these numbers in your reply did not come from a tool result this turn: "
            + ", ".join(sorted(set(bad)))
            + ". Call get_product_info / check_stock / search_products and only quote the exact prices and quantities they return."
        )
    deps.facts_checked = checked
    return output


@shop_agent.instructions
def shopper_context(ctx: RunContext[ShopDeps]) -> str:
    """Per-request context: who is chatting and which page they're on."""
    deps = ctx.deps
    lines = ["## Current context (from the server, trustworthy)"]
    if deps.customer:
        c = deps.customer
        lines.append(f"- Shopper: logged in as {c.first_name} {c.last_name} ({c.email}). Their earlier chats with you are in the message history.")
    else:
        lines.append("- Shopper: guest (not logged in). You don't know their name or email; suggest logging in if they want you to remember the chat.")
    lines.append(f"- Page they are on: {deps.page_path}")
    if p := deps.viewed_product:
        lines.append(
            f"- They are viewing the product page for **{p.name}** (product_id `{p.product_id}`, {p.garment_type}, "
            f"${p.price:.2f}, colors: {', '.join(p.colors)}). Words like \"this\", \"it\", or \"this one\" refer to this product "
            "unless they clearly mean something else. Still call tools for stock."
        )
    return "\n".join(lines)


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for turn in history[-20:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def run_chat(message: str, history: list[ChatTurn], deps: ShopDeps) -> ChatResponse:
    deps.user_message = message
    started = datetime.now(timezone.utc)
    trail = dict(
        started=started, user_id=deps.customer.id if deps.customer else None, page_path=deps.page_path,
        viewed_product=deps.viewed_product.product_id if deps.viewed_product else None, message=message, model=MODEL_NAME,
    )
    with capture_run_messages() as run_messages:
        try:
            result = await shop_agent.run(
                message, deps=deps, message_history=to_message_history(history), usage_limits=USAGE_LIMITS
            )
        except UsageLimitExceeded as e:
            audit.log_run(**trail, messages=run_messages[len(history):], stop_reason="usage_limit", error=str(e))
            raise
        except UnexpectedModelBehavior as e:
            reason = "fact_check_failed" if "retries" in str(e).lower() else "model_error"
            audit.log_run(**trail, messages=run_messages[len(history):], stop_reason=reason, error=str(e))
            raise
        except Exception as e:
            audit.log_run(**trail, messages=run_messages[len(history):], stop_reason="error", error=f"{type(e).__name__}: {e}")
            raise

    out = result.output
    results = None
    if out.matches:
        # Only show products a tool actually returned this run, and build cards from the DB (never from model text).
        ids = [pid for pid in out.matches.product_ids if pid in deps.seen_product_ids]
        cards = product_cards(ids)
        if cards:
            results = PageResults(title=out.matches.title, products=cards)
    response = ChatResponse(reply=out.reply, results=results, verified=deps.facts_checked > 0)
    u = result.usage
    audit.log_run(
        **trail, messages=result.new_messages(), stop_reason="final_output", reply=out.reply,
        shown_products=len(results.products) if results else 0, verified=response.verified,
        usage={"requests": u.requests, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens},
    )
    return response
