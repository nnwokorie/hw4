# Campus Customs — Storefront Design

Kept the existing clean look (white background, Yale blue `#00356B`, serif headings, square buttons) and added the pieces that make it feel like a real store.

| # | What I changed | Why it helps customers stick around and buy |
|---|---|---|
| 1 | **Home hero with real products:** a full-width Yale-blue banner with a tilted photo collage of 4 items (Big Yale hoodie, 2025 Harvard–Yale tee, Champion crewneck, coral tri-blend tee). Each photo links to its product page. White "Shop the collection" button. | Shoppers see merch in the first second instead of a paragraph of text. The photos are clickable shortcuts into the catalogue. |
| 2 | **"Shop by category" tiles:** Hoodies (27), Crewnecks (29), Tees (25), Quarter-Zips (11), each with a product photo and a style count. They open `/products?category=…` with that filter already on (the URL param also works from the footer links). | One click from landing to the right part of the store. The counts show there's plenty to choose from. |
| 3 | **"Staff picks · Game day ready" row:** a swipeable row of 8 curated items (Harvard–Yale, Boola Boola, Champion). Called "staff picks", not "bestsellers", because we have no sales data. | Gives browsers a reason to keep scrolling, and puts rivalry and spirit items in front of fans. |
| 4 | **Honest urgency badges + better product page:** cards show **"Only N left"** (≤ 20 total units), **"Sold out in L"**, or **"Limited sizes"**, all computed from live inventory. Product pages got a **breadcrumb trail** (Home / Products / Tees / item), **size buttons** (sold-out sizes striped and disabled; picking one shows "✓ 15 in stock in M" or "Only 2 left in XL. Don't wait!"), and a **"You may also like"** row (same category, closest price, in stock). | Real scarcity nudges a purchase without lying. Size buttons are faster to read than a stock table, and dead ends are avoided. "You may also like" keeps people browsing instead of leaving. |
| 5 | **Storefront framing:** a thin navy announcement bar ("Officially licensed Yale apparel · Live stock on every item · Questions? Ask Handsome Dan 🐶"), a trust strip on Home (Officially licensed / Live stock / Ask Handsome Dan), and a full blue footer with Shop, Help, and About columns. | Looks like a real, trustworthy store, which matters before someone creates an account or buys. The footer gives a second way to navigate from the bottom of any page. |
| + | **"Ask Handsome Dan 🐶"** chat button and header. The agent's prompt now introduces it as Handsome Dan, the bulldog shop assistant (after Yale's mascot). | A named, on-brand mascot is friendlier and more clickable than "Chat", so more shoppers use the assistant. |

**What I deliberately didn't add:** made-up promotions ("free shipping", "% off", "bestseller"). The store has no such policies or data, and the site should be as honest as the chatbot.

**Checked in the app:**
- Boola Boola tee: badge "Sold out in L", L button disabled, XL → "Only 2 left", M → "15 in stock" (DB: L=0, XL=2, M=15).
- The Hoodies tile and footer link open `/products?category=hoodie` with 27 items.
- The breadcrumb reads Home / Products / Tees / Boola Boola T Shirt.

**Files:**
- `frontend/src/pages/Home.tsx`, `ProductDetail.tsx`, `Products.tsx`
- `frontend/src/components/ProductCard.tsx`, `ChatWidget.tsx`
- `frontend/src/stock.ts` (badge rules), `frontend/src/App.tsx` (announcement bar + footer), `frontend/src/index.css`
- `backend/prompts/prompt.md` (Handsome Dan name)
