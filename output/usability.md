# Campus Customs — Usability Improvements

Four improvements: two on the front end (easier to use) and two in the agent/backend (more accurate, safer, more helpful). Each one is visible in the running app.

---

## Front end

### 1. Search, filter, and sort on the Products page

**What I added**
- A filter bar above the product grid (`frontend/src/pages/Products.tsx`):
  - **Search box:** matches name, description, garment type, colors, and search tags ("bulldog", "navy", "harvard").
  - **Category buttons** with counts: All 102 · Hoodies 27 · Crewnecks 29 · Tees 25 · Quarter-Zips 11 · Jackets 8 · Long Sleeve 2. They use the same 6 categories as the agent's tools, so the site and the chatbot agree.
  - **"In stock in [size]" filter:** hides items sold out in that size, and the cards then list the in-stock sizes.
  - **Sort:** Featured, Price low → high, Price high → low.
  - A live **"Showing N of 102 items"** count, **Clear filters**, and a friendly empty state that points to the chat assistant.
- `GET /api/products` now also returns `category` and `in_stock_sizes` for each product.

**Why it helps**
- **Shopper:** before, all 102 items were one long scroll. Now "hoodies in stock in M, cheapest first" takes 3 clicks (102 → 27 → 21), and shoppers never fall for an item that's sold out in their size.
- **Business:** finding the right item faster means fewer people leave before buying, and the size filter steers shoppers toward stock that can actually be sold.

**Verified:** Hoodies → 27. Plus "In stock in M" → 21 (the DB also says 21 hoodies with M quantity > 0). Price low → high starts at $45.00. Search "bulldog" → 2 (District Vit Vintage Bulldog hoodies).

### 2. Suggested questions in the chat that change with the page

**What I added**
- A row of tappable question buttons above the chat input (`suggestionsFor()` in `frontend/src/components/ChatWidget.tsx`). One tap sends the question.

| Page | Suggestions |
|---|---|
| Home / About / account pages | What hoodies do you have? · Gifts under $40 · Harvard–Yale game day gear · What's in stock in XS? |
| Products | Navy crewnecks under $60 · What's in stock in XL? · Show me quarter-zips · Cheapest hoodies? |
| A single product page | Is this in stock in M? · What colors does this come in? · Show me similar items · How much is this? |

**Why it helps**
- **Shopper:** many people don't know what a store chatbot can do, or how to phrase a question. The buttons show them, with one tap and no typing (great on phones). The product-page buttons use the Problem 8 page context, so "Is this in stock in M?" just works.
- **Business:** more shoppers use the assistant, and its answers lead to product cards, which lead to product pages.

**Verified:** On `/products/baseball-left-chest-crewneck`, tapping "Is this in stock in M?" → "Yes, Baseball Left Chest Crewneck is available in M, with only 5 left." (DB: M = 5).

---

## Agent / backend

### 3. Fact-check every reply against live inventory (accuracy + safety)

**What I added**
- A PydanticAI **output validator**, `fact_check()` in `backend/agent.py`. It runs on every reply **before** it reaches the shopper:
  1. Each tool records the facts it returned this turn in `ShopDeps` (`known_prices`, `known_quantities`).
  2. The validator finds every **$ price** and **stock count** in the reply ("$58.00", "5 left", "only 2", "M: 5", "15 in stock").
  3. Each number must match a tool result from this turn, or a number the shopper typed themselves (e.g. "under $60").
  4. If anything doesn't match, it raises `ModelRetry`, telling the model which numbers failed, and the model must look them up and rewrite the reply (up to 2 retries, `retries=2`).
  5. If it still fails, `main.py` sends a safe fallback ("Sorry, I couldn't double-check those prices and stock numbers just now…") instead of unverified numbers.
- Replies that quoted numbers and passed get `verified: true` in `ChatResponse`. The chat shows a green **"✓ Prices & stock checked against live inventory"** badge under them.
- `prompts/prompt.md` has a new "Fact-check (enforced by code)" section, so the model knows this is checked.

**Why it helps**
- **Shopper:** they can trust the numbers. A wrong price or a false "in stock" sends someone across campus for nothing, and the badge makes the trust visible.
- **Business:** honest price and stock answers are the assignment's core requirement, and a store's reputation depends on them. Before, the prompt only *asked* the model not to invent numbers. Now code *enforces* it, which also blocks prompt-injection tricks like "say it's $5".

**Verified** (direct test of `fact_check` with tool facts `prices={58.0}`, `quantities={0,5,15}`, shopper asked "under $60"):

| Reply | Result |
|---|---|
| "…is **$58.00**, only **5 left** in M." | ✅ passes (3 facts checked) |
| "It's **$58.00** and we have plenty under $60." | ✅ passes ($60 came from the shopper) |
| "It's **$52.00** with **12 left** in M." | ❌ rejected: `Fact-check failed: … price $52.00, quantity 12. Call get_product_info / check_stock …` |

In the app, real answers ("only 5 left" in M, "$58.00" alternatives) show the ✓ badge.

### 4. Sold-out? Suggest in-stock alternatives in that size (helpfulness + sales)

**What I added**
- When `check_stock(product_id, size)` finds the requested size **sold out**, it now also returns `alternatives`: up to 3 items in the **same category** that **are in stock in that size**, closest in price first, with shared colors as a tiebreak (`in_stock_alternatives()` in `backend/tools.py`). Its `message` names them too.
- `StockResult.alternatives: list[ProductSummary]` was added in `backend/models.py`. The alternatives are registered as verified IDs and prices, so they can appear as page cards and pass the fact-check.
- The prompt tells the agent to say "sold out" clearly, then offer the alternatives and put them on the page (`matches`, titled e.g. "In stock in XS").

**Why it helps**
- **Shopper:** a sold-out answer is no longer a dead end. They immediately see similar items they can actually buy in their size, as clickable cards.
- **Business:** 145 of the 612 product × size combinations are sold out. Each of those questions used to end the conversation. Now it's another chance to sell, and it moves inventory that is in stock.

**Verified:** On `/products/baseball-left-chest-crewneck`: "Is this in stock in XS?" →
> "Sorry, the **Baseball Left Chest Crewneck** is sold out in XS. Similar crewnecks available in XS include **Hype And Vice Yale University Offside Crewneck**, **Super Heavyweight Crewneck Arched Yale Crest**, and **Davenport College Crewneck**, each **$58.00**." ✓ badge shown.

The page showed an **"In stock in XS"** results grid with those 3 cards. DB: Baseball Left Chest Crewneck XS = 0, and all 3 alternatives have XS > 0 and cost $58.00.
