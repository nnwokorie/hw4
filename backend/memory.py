"""Customer memory: who is chatting, where they are on the site, and their saved chat history.

History lives in the existing `chat_messages` table (one row per message). `products_json` holds
the product cards shown with an assistant reply, in the same list-of-products format as the seed rows.
"""

import json
import re

from models import ChatResponse, ChatTurn, CustomerInfo, HistoryMessage, PageContext, PageResults, ViewedProduct
from audit import redact
from tools import get_db, product_cards, product_from_row

AGENT_HISTORY_TURNS = 20  # messages fed back to the agent as context
UI_HISTORY_MESSAGES = 50  # messages shown when the chat widget reloads


def load_customer(user_id: int | None) -> CustomerInfo | None:
    if user_id is None:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT id, first_name, last_name, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    first, last = row["first_name"], row["last_name"]
    if not first:  # older rows may only have `name`
        first, _, last = row["name"].partition(" ")
    return CustomerInfo(id=row["id"], first_name=first, last_name=last or "", email=row["email"])


def resolve_page(page: PageContext) -> tuple[str, ViewedProduct | None]:
    """Trust only what we can verify: the product id must exist in the catalogue."""
    product_id = page.product_id
    if not product_id and (m := re.fullmatch(r"/products/([\w-]+)", page.path)):
        product_id = m.group(1)
    if not product_id:
        return page.path, None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return page.path, None
    p = product_from_row(row)
    return page.path, ViewedProduct(
        product_id=p["product_id"], name=p["name"], garment_type=p["garment_type"], price=p["price"], colors=p["colors"]
    )


def load_agent_history(user_id: int) -> list[ChatTurn]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, AGENT_HISTORY_TURNS),
        ).fetchall()
    return [ChatTurn(role=r["role"], content=r["content"]) for r in reversed(rows) if r["role"] in ("user", "assistant")]


def save_exchange(user_id: int, message: str, response: ChatResponse) -> None:
    products = [p.model_dump() for p in response.results.products] if response.results else []
    with get_db() as conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, redact(message)))
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, redact(response.reply), json.dumps(products)),
        )


def load_ui_history(user_id: int) -> list[HistoryMessage]:
    """Saved messages for the widget. Product cards are rebuilt from the DB so prices/stock are current."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, UI_HISTORY_MESSAGES),
        ).fetchall()
    out: list[HistoryMessage] = []
    last_user_text = ""
    for r in reversed(rows):
        if r["role"] == "user":
            last_user_text = r["content"]
        results = None
        if r["role"] == "assistant" and r["products_json"]:
            try:
                ids = [p["product_id"] for p in json.loads(r["products_json"]) if isinstance(p, dict) and "product_id" in p]
            except (ValueError, TypeError):
                ids = []
            cards = product_cards(ids)
            if cards:
                results = PageResults(title=f"Results for “{last_user_text[:50]}”", products=cards)
        out.append(HistoryMessage(id=r["id"], role=r["role"], content=r["content"], created_at=r["created_at"], results=results))
    return out
