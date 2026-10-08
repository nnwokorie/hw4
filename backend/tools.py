"""Database helpers and the tools the shop agent can call. All price/stock facts come from SQLite."""

import json
import re
import sqlite3
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    LookupFailed,
    ProductCard,
    ProductInfo,
    ProductSummary,
    SearchResult,
    ShopDeps,
    SizeAvailability,
    SizeStock,
    StockResult,
    stock_status,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# garment_type in the DB is free text (22 variants); map to a few shopper-friendly categories.
CATEGORIES = {
    "hoodie": ["hoodie", "hooded"],
    "crewneck": ["crewneck", "mockneck"],
    "t-shirt": ["t-shirt"],
    "quarter-zip": ["quarter-zip"],
    "jacket": ["jacket"],
    "long-sleeve": ["long-sleeve"],
}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def category_of(garment_type: str) -> str:
    g = garment_type.lower()
    for cat, words in CATEGORIES.items():
        if any(w in g for w in words):
            return cat
    return "other"


def product_from_row(row: sqlite3.Row) -> dict:
    """Catalogue row -> JSON-ready dict with parsed lists and an image URL."""
    p = dict(row)
    p["colors"] = json.loads(p["colors"])
    p["search_tags"] = json.loads(p["search_tags"])
    p["image_url"] = "/images/" + Path(p.pop("image_file_path")).name
    return p


def stock_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    stock = [SizeStock(size=r["size"], quantity=r["quantity"]) for r in rows]
    return sorted(stock, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Build cards for the given IDs straight from the DB; unknown IDs are dropped."""
    cards = []
    with get_db() as conn:
        for pid in dict.fromkeys(product_ids):
            row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
            if row is None:
                continue
            p = product_from_row(row)
            cards.append(ProductCard(
                **{k: p[k] for k in ("product_id", "name", "garment_type", "price", "image_url", "description", "colors")},
                in_stock_sizes=[s.size for s in stock_for(conn, pid) if s.quantity > 0],
            ))
    return cards


# Shopper wording -> inventory size codes.
SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
}


# Shopper color words -> catalogue color words (catalogue uses names like "dusty coral", "heather gray").
COLOR_FAMILIES = {
    "pink": ["pink", "coral", "rose", "salmon", "blush", "magenta"],
    "red": ["red", "crimson", "maroon", "burgundy"],
    "blue": ["blue", "navy", "royal"],
    "navy": ["navy"],
    "gray": ["gray", "grey", "heather", "charcoal", "silver"],
    "grey": ["gray", "grey", "heather", "charcoal", "silver"],
    "white": ["white", "cream", "ivory", "natural", "oatmeal"],
    "cream": ["cream", "ivory", "natural", "oatmeal", "off-white"],
    "green": ["green", "olive", "forest"],
    "yellow": ["yellow", "gold"],
    "orange": ["orange"],
    "purple": ["purple", "violet", "lavender"],
    "black": ["black"],
}


def color_matches(wanted: str, colors: list[str]) -> bool:
    words = COLOR_FAMILIES.get(wanted.strip().lower(), [wanted.strip().lower()])
    return any(w in c.lower() for c in colors for w in words)


def normalize_size(size: str) -> str | None:
    return SIZE_ALIASES.get(size.strip().lower())


def _find_product(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()


def _not_found(product_id: str) -> LookupFailed:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT product_id FROM catalogue WHERE product_id LIKE ? LIMIT 5", (f"%{product_id.strip()[:20]}%",)
        ).fetchall()
    return LookupFailed(
        error=f"No product with id {product_id!r}. Use search_products to find the right product_id.",
        suggestions=[r["product_id"] for r in rows],
    )


# ---------- agent tools ----------

def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    category: str | None = None,
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    limit: int = 12,
) -> SearchResult:
    """Find products in the catalogue. Use this first to get product_ids.

    Args:
        query: Free-text keywords, e.g. "harvard game", "baseball", "big yale". Empty = no keyword filter.
        category: One of hoodie, crewneck, t-shirt, quarter-zip, jacket, long-sleeve.
        color: Color word to match, e.g. "navy", "gray", "pink" (color families included, so "pink" finds "dusty coral").
        size: Only return items with this size in stock (XS, S, M, L, XL, XXL, or words like "medium").
        max_price: Only return items at or below this price in USD.
        limit: Max results (1-30). Use 30 for broad "what X do you have" questions.
    """
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in {"yale", "the", "a", "and", "shirt"}]
    size_code = normalize_size(size) if size else None
    results = []
    with get_db() as conn:
        for row in conn.execute("SELECT * FROM catalogue"):
            p = product_from_row(row)
            if category and category_of(p["garment_type"]) != category.lower():
                continue
            if color and not color_matches(color, p["colors"]):
                continue
            if max_price is not None and p["price"] > max_price:
                continue
            haystack = " ".join([p["name"], p["description"], p["garment_type"], *p["colors"], *p["search_tags"]]).lower()
            score = sum(haystack.count(w) for w in words)
            if words and score == 0:
                continue
            in_stock = [s.size for s in stock_for(conn, p["product_id"]) if s.quantity > 0]
            if size_code and size_code not in in_stock:
                continue
            results.append((score, ProductSummary(
                product_id=p["product_id"], name=p["name"], category=category_of(p["garment_type"]),
                price=p["price"], colors=p["colors"], in_stock_sizes=in_stock,
            )))
    results.sort(key=lambda r: (-r[0], r[1].name))
    products = [r[1] for r in results[: max(1, min(limit, 30))]]
    ctx.deps.seen_product_ids.update(p.product_id for p in products)
    ctx.deps.known_prices.update(p.price for p in products)
    ctx.deps.known_quantities.update({len(results), len(products)})  # total matches and number shown
    return SearchResult(query=query, total_matches=len(results), products=products)


def get_product_info(ctx: RunContext[ShopDeps], product_id: str) -> ProductInfo | LookupFailed:
    """Get the real description and price for one product. Call this for any price or description question.

    Args:
        product_id: The product_id from search_products.
    """
    with get_db() as conn:
        row = _find_product(conn, product_id)
        if row is None:
            return _not_found(product_id)
        p = product_from_row(row)
        sizes = [s.size for s in stock_for(conn, p["product_id"])]
    ctx.deps.seen_product_ids.add(p["product_id"])
    ctx.deps.known_prices.add(p["price"])
    return ProductInfo(
        product_id=p["product_id"], name=p["name"], garment_type=p["garment_type"],
        description=p["description"], price=p["price"], colors=p["colors"], sizes_offered=sizes,
    )


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockResult | LookupFailed:
    """Get exact stock counts from inventory. Call this for any availability / "how many" / size question.

    Args:
        product_id: The product_id from search_products.
        size: Optional size the shopper asked about (XS, S, M, L, XL, XXL, or words like "medium").
              Leave empty to get every size.
    """
    with get_db() as conn:
        row = _find_product(conn, product_id)
        if row is None:
            return _not_found(product_id)
        stock = stock_for(conn, row["product_id"])
    ctx.deps.seen_product_ids.add(row["product_id"])
    ctx.deps.known_prices.add(row["price"])
    ctx.deps.known_quantities.update(s.quantity for s in stock)
    ctx.deps.known_quantities.add(sum(s.quantity for s in stock))

    size_code = None
    if size:
        size_code = normalize_size(size)
        if size_code is None or size_code not in {s.size for s in stock}:
            return LookupFailed(error=f"Size {size!r} is not offered for {row['name']}.", suggestions=[s.size for s in stock])

    sizes = [SizeAvailability(size=s.size, quantity=s.quantity, status=stock_status(s.quantity)) for s in stock]
    sold_out = [s.size for s in sizes if s.status == "sold_out"]
    shown = [s for s in sizes if s.size == size_code] if size_code else sizes

    if size_code:
        s = shown[0]
        message = (f"{row['name']} in {s.size} is SOLD OUT." if s.status == "sold_out"
                   else f"{row['name']} in {s.size}: {s.quantity} in stock" + (" (low stock)." if s.status == "low_stock" else "."))
    elif len(sold_out) == len(sizes):
        message = f"{row['name']} is sold out in every size."
    else:
        message = f"{row['name']}: " + ", ".join(f"{s.size} {s.quantity}" for s in sizes) + (
            f". Sold out in {', '.join(sold_out)}." if sold_out else ". All sizes in stock.")

    alternatives = []
    if size_code and shown[0].status == "sold_out":
        alternatives = in_stock_alternatives(row, size_code)
        ctx.deps.seen_product_ids.update(a.product_id for a in alternatives)
        ctx.deps.known_prices.update(a.price for a in alternatives)
        if alternatives:
            message += f" Similar items in stock in {size_code}: " + ", ".join(f"{a.name} (${a.price:.2f})" for a in alternatives) + "."

    return StockResult(
        product_id=row["product_id"], name=row["name"], price=row["price"], requested_size=size_code,
        sizes=shown, total_in_stock=sum(s.quantity for s in sizes), sold_out_sizes=sold_out,
        alternatives=alternatives, message=message,
    )


def in_stock_alternatives(row: sqlite3.Row, size: str, limit: int = 3) -> list[ProductSummary]:
    """Same-category items that are in stock in `size`, closest in price first (plus shared colors as a tiebreak)."""
    target = product_from_row(row)
    cat = category_of(target["garment_type"])
    picks = []
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.* FROM catalogue c JOIN inventory i ON i.product_id = c.product_id
               WHERE i.size = ? AND i.quantity > 0 AND c.product_id != ?""",
            (size, target["product_id"]),
        ).fetchall()
        for r in rows:
            p = product_from_row(r)
            if category_of(p["garment_type"]) != cat:
                continue
            shared = len(set(p["colors"]) & set(target["colors"]))
            picks.append((abs(p["price"] - target["price"]), -shared, p))
        picks.sort(key=lambda t: (t[0], t[1], t[2]["name"]))
        return [
            ProductSummary(
                product_id=p["product_id"], name=p["name"], category=cat, price=p["price"], colors=p["colors"],
                in_stock_sizes=[s.size for s in stock_for(conn, p["product_id"]) if s.quantity > 0],
            )
            for _, _, p in picks[:limit]
        ]


def get_customer_profile(ctx: RunContext[ShopDeps]) -> dict:
    """Who is chatting: name and email of the logged-in shopper, or guest. Use if asked "who am I?" or similar."""
    c = ctx.deps.customer
    if c is None:
        return {"logged_in": False}
    return {"logged_in": True, "first_name": c.first_name, "last_name": c.last_name, "email": c.email}


def get_current_page(ctx: RunContext[ShopDeps]) -> dict:
    """Which page the shopper is on, and the product they are viewing (if any). Use to resolve "this" / "it"."""
    p = ctx.deps.viewed_product
    if p:
        ctx.deps.seen_product_ids.add(p.product_id)
        ctx.deps.known_prices.add(p.price)
    return {"path": ctx.deps.page_path, "viewing_product": p.model_dump() if p else None}


SHOP_TOOLS = [search_products, get_product_info, check_stock, get_customer_profile, get_current_page]
