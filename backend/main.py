"""Campus Customs API: products, images, auth, and the shop chatbot agent.

Run from backend/:  uvicorn main:app --reload --port 8000
"""

import io
import logging
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.exceptions import UnexpectedModelBehavior
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from agent import run_chat
from auth import current_user_id
from auth import router as auth_router
from memory import load_agent_history, load_customer, load_ui_history, resolve_page, save_exchange
from models import ChatRequest, ChatResponse, HistoryMessage, ShopDeps
from tools import DATA_DIR, SIZE_ORDER, category_of, get_db, product_from_row

app = FastAPI(title="Campus Customs API")
app.include_router(auth_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=512)
def white_background_jpeg(path: Path) -> bytes:
    """Many product photos have black backgrounds; replace them with white (like the real site).
    The original files in data/products are never modified.

    Background = neutral near-black pixels connected to the photo's edge. Neutral matters: dark navy
    fabric has a higher blue channel than black, so it isn't mistaken for background. The mask is
    de-speckled, grown 2px to swallow the dark JPEG fringe, and feathered so edges look smooth.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    if max(sum(im.getpixel(c)) for c in corners) >= 60:
        out = im  # already a light background
    else:
        r, g, b = im.filter(ImageFilter.MedianFilter(5)).split()  # median ignores JPEG noise
        bright = ImageChops.lighter(ImageChops.lighter(r, g), b)
        blue_tint = ImageChops.subtract(b, r)
        dark = ImageChops.multiply(Image.eval(bright, lambda v: 255 if v < 26 else 0),
                                   Image.eval(blue_tint, lambda v: 255 if v < 7 else 0))
        for c in corners:
            if dark.getpixel(c) == 255:
                ImageDraw.floodfill(dark, c, 128)
        mask = Image.eval(dark, lambda v: 255 if v == 128 else 0)
        mask = mask.filter(ImageFilter.MedianFilter(7)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
        out = Image.composite(Image.new("RGB", im.size, (255, 255, 255)), im, mask)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=92)
    return buf.getvalue()


@app.on_event("startup")
def warm_image_cache() -> None:
    """Pre-process every product photo in the background so chat result cards show images instantly."""
    paths = sorted((DATA_DIR / "products").glob("*.jpg"))
    threading.Thread(target=lambda: [white_background_jpeg(p.resolve()) for p in paths], daemon=True).start()


@app.get("/images/{filename}")
def product_image(filename: str) -> Response:
    path = (DATA_DIR / "products" / filename).resolve()
    if path.parent != (DATA_DIR / "products").resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(
        white_background_jpeg(path),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/products")
def list_products() -> list[dict]:
    """All products plus `category` and `in_stock_sizes` so the Products page can filter by type and size."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    by_product: dict[str, dict[str, int]] = {}
    for r in stock:
        by_product.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    out = []
    for r in rows:
        p = product_from_row(r)
        sizes = by_product.get(p["product_id"], {})
        p["category"] = category_of(p["garment_type"])
        p["in_stock_sizes"] = [s for s in SIZE_ORDER if sizes.get(s, 0) > 0]
        p["total_stock"] = sum(sizes.values())
        out.append(p)
    return out


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
    product = product_from_row(row)
    product["sizes"] = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return product


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    customer = load_customer(current_user_id(request))  # identity comes from the session cookie only
    page_path, viewed_product = resolve_page(body.page)
    deps = ShopDeps(customer=customer, page_path=page_path, viewed_product=viewed_product)
    if viewed_product:  # verified against the catalogue, so it may appear as a result card
        deps.seen_product_ids.add(viewed_product.product_id)
    # Logged in: history comes from the database. Guest: from the browser (not saved).
    history = load_agent_history(customer.id) if customer else body.history
    try:
        response = await run_chat(body.message, history, deps)
    except UnexpectedModelBehavior:
        # The reply kept failing the fact-check: never send unverified numbers to the shopper.
        logging.warning("fact-check retries exhausted for message: %r", body.message[:200])
        response = ChatResponse(reply="Sorry, I couldn't double-check those prices and stock numbers just now. "
                                      "Please check the product page for the latest details, or ask me again.")
    except Exception:
        logging.exception("chat agent failed")
        raise HTTPException(status_code=502, detail="The assistant is unavailable right now. Please try again.")
    if customer:
        save_exchange(customer.id, body.message, response)
    return response


@app.get("/api/chat/history")
def chat_history(request: Request) -> list[HistoryMessage]:
    """Saved chat for the logged-in shopper (empty for guests)."""
    user_id = current_user_id(request)
    return load_ui_history(user_id) if user_id is not None else []
