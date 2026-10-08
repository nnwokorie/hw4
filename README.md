# Campus Customs — Shop + Chatbot (HW 4)

A Campus Customs storefront (React + Vite + TypeScript) with a FastAPI backend whose brain is a PydanticAI agent, **Handsome Dan**. Shoppers can browse and filter products, create an account and log in, and chat about merch. Matching items appear on the page as product cards, and every price and stock number comes from the local SQLite database.

```
hw4/
├── AI_prompts.md          # log of prompts typed to the vibe coder, one section per problem
├── requirements.txt       # backend Python packages
├── .env.example           # copy to .env and add your key
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app: run with `uvicorn main:app --reload --port 8000`
│   ├── agent.py           # agent wiring, context, fact-check, audit
│   ├── models.py          # Pydantic / PydanticAI types
│   ├── tools.py           # read-only database tools
│   ├── prompts/prompt.md  # system prompt
│   ├── auth.py            # sign up / log in (PBKDF2 hashes, signed cookie)
│   ├── memory.py          # who's chatting, page context, saved chat history
│   └── audit.py           # append-only audit trail + redaction
└── output/                # harness.md, design.md, usability.md, app_check.html (+ images), audit_trail.json
```

## 1. Place the data pack (not in git)

Unzip `data.zip` so this folder has:

```
hw4/data/
├── campus_customs.db
└── products/              # product images referenced by the catalogue table
```

## 2. Add your API key

```bash
cp .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY`. The agent uses OpenAI `gpt-5.6-luna` through Portkey.

## 3. Run the backend (FastAPI on port 8000)

Requires Python 3.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

## 4. Run the front end (Vite on port 5174)

Requires Node 20+. In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --port 5174
```

Open **http://localhost:5174**. Vite proxies `/api` and `/images` to the backend on port 8000. Product photos appear a few seconds after the backend starts, while white-background versions are prepared.

**Test account:** `test@campuscustoms.yale.edu` (password from the assignment), or create your own on **Create Account**.

## Things to try
- Chat: "What hoodies do you have?" puts a grid of hoodie cards on the page.
- On a product page: "Do you have this in XL?" gives exact stock, or "sold out" plus in-stock alternatives.
- Products page: search, category buttons, "In stock in M", and sort by price.
- Log in, chat, log out, log back in: your chat history reloads.

## Docs
- `output/harness.md`: how the whole system works (data, auth, architecture, memory, models, tools, safety rules, specs, audit trail)
- `output/usability.md`, `output/design.md`: improvements and design changes
- `output/app_check.html`: screenshots of the live checks (open in a browser)
- `output/audit_trail.json`: append-only log of agent runs
