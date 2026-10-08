"""Pydantic / PydanticAI types shared by the API and the agent."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


class CustomerInfo(BaseModel):
    """Who is chatting. Loaded server-side from the session cookie, never from the request body."""

    id: int
    first_name: str
    last_name: str
    email: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message (sent by the front end)."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120)


class ViewedProduct(BaseModel):
    """The product page the shopper is looking at, verified against the catalogue."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]


@dataclass
class ShopDeps:
    """Per-request context handed to the agent's instructions and tools."""

    customer: CustomerInfo | None = None  # None = guest
    page_path: str = "/"
    viewed_product: ViewedProduct | None = None
    # product_ids that tools actually returned this run; page results are limited to these.
    seen_product_ids: set[str] = field(default_factory=set)
    # Facts the tools returned this run; the reply fact-checker only allows these numbers.
    user_message: str = ""
    known_prices: set[float] = field(default_factory=set)
    known_quantities: set[int] = field(default_factory=set)
    facts_checked: int = 0


MAX_PAGE_RESULTS = 30


class ProductMatches(BaseModel):
    """Structured search results the agent hands to the website to show as product cards."""

    title: str = Field(max_length=60, description='Short heading for the results, e.g. "Hoodies" or "Navy items under $50".')
    product_ids: list[str] = Field(
        max_length=MAX_PAGE_RESULTS,
        description="product_ids from search_products results, best match first. Never invent IDs.",
    )


class AgentReply(BaseModel):
    """Structured output the agent must return."""

    reply: str = Field(description="Friendly answer to the shopper, in Campus Customs voice. Markdown allowed.")
    matches: ProductMatches | None = Field(
        default=None,
        description="Products to show on the page as cards. Set whenever the reply is about specific items or a type of item; null for chit-chat or general questions.",
    )


class SizeStock(BaseModel):
    size: str
    quantity: int


# ---------- tool return types (what the agent sees) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]
LOW_STOCK_THRESHOLD = 5


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


class ProductSummary(BaseModel):
    """One search hit: just enough to pick the right product, then look it up."""

    product_id: str
    name: str
    category: str
    price: float
    colors: list[str]
    in_stock_sizes: list[str]


class SearchResult(BaseModel):
    query: str
    total_matches: int
    products: list[ProductSummary]


class ProductInfo(BaseModel):
    """Description + price for one product, straight from `catalogue`."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    currency: Literal["USD"] = "USD"
    colors: list[str]
    sizes_offered: list[str]


class SizeAvailability(BaseModel):
    size: str
    quantity: int = Field(description="Exact units in stock from `inventory`.")
    status: StockStatus


class StockResult(BaseModel):
    """Stock for one product, from `inventory`. If `requested_size` is set, `sizes` holds only that size."""

    product_id: str
    name: str
    price: float
    requested_size: str | None
    sizes: list[SizeAvailability]
    total_in_stock: int
    sold_out_sizes: list[str]
    alternatives: list["ProductSummary"] = Field(
        default_factory=list,
        description="When the requested size is sold out: similar items that ARE in stock in that size. Offer these.",
    )
    message: str = Field(description="Plain-English summary the agent can rely on.")


class LookupFailed(BaseModel):
    """Returned instead of a result when the product or size doesn't exist."""

    error: str
    suggestions: list[str] = Field(default_factory=list)


class ProductCard(BaseModel):
    """Product shown in chat / on the page. Always built from the database, never from model text."""

    product_id: str
    name: str
    garment_type: str
    price: float
    image_url: str
    description: str
    colors: list[str]
    in_stock_sizes: list[str]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests; logged-in history is loaded from the chat_messages table.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext = Field(default_factory=PageContext)


class PageResults(BaseModel):
    """What the website renders as the dynamic results grid."""

    title: str
    products: list[ProductCard]


class ChatResponse(BaseModel):
    reply: str
    results: PageResults | None = None
    # True when the reply quoted prices/stock and every number passed the fact-check.
    verified: bool = False


class HistoryMessage(BaseModel):
    """One saved chat message, as returned by GET /api/chat/history."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    results: PageResults | None = None
