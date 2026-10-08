# Homework 4 — AI Prompt Log

## Problem 1 — Vibe Coder Prompts

Prompt typed:

“Context for HW 4, put this in my HW 4 folder in AI Foundations!”

Follow-up prompt:

“Dont do it by the panels, but by problems so question 1,2,3 you dont need to add the context so you can remove but keep the prompts.md file”

What was lacking after the first prompt:

The first version added a separate context file and organized things by panel instead of keeping one prompt-log section per problem.

## Problem 2 — Analyze the Database

Prompt typed:

“look at the database data/campus_customs.db and understand the fields in each table. Min should include catalogue, inventory, and users but add more if you think. Do this quickly please.”

Follow-up prompt:

“start the file output/harness.md and write down each table and its fields and one short line on why each field matters for the shop or the chatbot. The harness file will continue to grow in later problems (models, tools, safety, specs)”

What was lacking after the first prompt:

The first pass summarized the tables but did not explain why each field matters, and it was not in the `output/harness.md` file that later problems build on.

## Problem 3 — Campus Customs Website

Prompt typed:

“Scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top that links to the main pages: Home, Products, About Us, Log In, Create Account. Pull campus customs-style wodring from yalbulldogblue.com for Home and About Us but write these pages in your own voice, include words like classic, clean, blue, collegiate style etc”

Follow-up prompt:

“Please delete wherever it says to use black pink for all web apps, I would rather it be blue. On the products page, show product images from the catalogue (use the image paths in the database) with basic product info (nam, price, short description). Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stock when you have them). Clicking a card on products should take the shopper there. Add a chat interface in the bottom right of the site (a floating chat panel is fine). IT does not need to tal kto an agent yet - a stub that will call you backend later is enough for this problem. Will need a small API soon to read the database. It is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5”

Second follow-up prompt:

“Can we give it all like a nice white background f or the clothes like the actual site and can the design be sleeker idk how to put that into coder terms, can you do this quickly though”

Third follow-up prompt:

“why do the items look fuzzy and weird”

What was lacking after the first prompt:

The first version only had the page shells: no real products, single-item pages, chat panel, or API, and the black-and-pink style and black photo backgrounds did not match the clean blue look of the real site.

## Problem 4 — Create Account and Login

Prompt typed:

“Problem 4, Create Account and Login. Build a normal create-account / login flow. Create account: first name, last name, email, password (confirm password too). Log In: email and password. New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them”

Follow-up prompt:

“Nice for the remaining part of question 4, the seed database has a test user you can use while building: Email: test@campuscustoms.yale.edu Password: [given in the assignment]. Confirm you can log in as that user, and that a brand-new account you create also works. Update output/harness.md with how auth works (what you store for a user and how passwords are protected).”

What was lacking after the first prompt:

The seed test user could not log in because its hashes use 120,000 PBKDF2 iterations instead of 600,000, so login now accepts that older format and upgrades it, and the auth design was not yet written in `output/harness.md`.

## Problem 5 — PydanticAI Agent Backend

Prompt typed:

“Build the shop chatbot as a PydanticAI agent behind FastAPI plugged into your front-end chat widget. Put the API app in backend/main.py - that is teh file you run with Uvicorn. Keep the agent as these four files next to it: backend/prompts/prompt.md - system prompt (grow this same file later), backend/agent.py - agent entry / wiring, backend/tools.py - tools the agent can call, backend/models.py - Pydantic / PydanticAI structured types. In main.py, expose a chat route so a message form the website returns a reply from the agent (and whatever else you need for products/auth). You would need your AI model API key for the agent. Put Campus Customs voice and safety basics into prompts/prompt.md (will expand on tools and safety later). Start or update types in models.py for chat replies / product cards as needed. In output/harness.md, note how the front end talks to FastAPR and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this uvicorn main:app --reload --port 8000. please do it efficiently and quickly”

## Problem 6 — Tools: Product Info and Stock

Prompt typed:

“Give the agent tools that look up real information from Campus_customs.db: product description, price, how many are in stock (by size when the customer asks). The agent must use the database - it should not invent prices or quantities. If a size is out of stock, say so clearly. Expand prompts/prompt.md so that the agent knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why”

## Problem 7 — Chat Search That Updates the Page

Prompt typed:

“Now we will add a neat feature to the site. When a customer asks about a type of item - for example "what hoodies do you have?" - the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info). This is an API contract: the agent returns structured product matches and then the front end renders them on the website. It looks really cool. After teh dynamic product cards are laoded by the new feature, make sure the same single-item page havior you built in Problem 3 still works, products should still open up when clicked. Update prompts/pompt.md and output/harness.md so it is clear how search results reach the page”

## Problem 8 — Customer Memory

Prompt typed:

“When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) - put that in agent deps (or an equivalent clear pattern) and/or tools the agent cant call. Also pass enough page context that if someone is on a product page and asks "do you have this in pink?". the agent knows which item they mean. Hint: you can put code into the agent context. Guests can still chat, but history only needs to persist for logged-in users. Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed”

## Problem 9 — Usability Improvements

Prompt typed:

“Need to improve it now, Can you give me some ideas for 2 front end usability improvements, 2 agent / backend usability improvements. Front end improvemetns are things that make the site easier to use. Backend improvements, make the agent out better more accurate safer. Write output/usability.md before or as you build. For each of the improvements say: what you added, Why it helps a campus customs shopper or the businesss. We need to make sure hte improvements show on the app, can you show me your thougths and suggestions first?”

Follow-up prompt:

“I like that lets do it quickly and efficiently”

What was lacking after the first prompt:

The first answer was only a list of suggestions, as asked; the follow-up approved building the four picks (product filters, page-aware chat suggestions, the reply fact-checker, and sold-out alternatives) and writing `output/usability.md`.

## Problem 10 — Style the Website

Prompt typed:

“Want to add creative design so the site feels like a real Campus Customs storefront, I mean I kind of like what we have now but any suggestions on design. Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short. Let's brainstorm”

Follow-up prompt:

“Yes please!”

What was lacking after the first prompt:

The first answer was a brainstorm only, as asked; the follow-up approved building the five recommended changes (product hero, category tiles, staff-picks row, honest stock badges and a better product page, storefront announcement bar and footer) plus the Handsome Dan chat button, and writing `output/design.md`.

## Problem 11 — Test the Live Site

Prompt typed:

“Test the live site and document it in output/app_check.html (a page you can double click open). Include clear screenshots and short captions for: Chat checking the inventory level of an item (honest stock/price from the DB), The dynamic search-result cards appearing after a category question (e.g. hoodies), One of the usability features you added in Problem 9. Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths for example App_check_images/inventory.png”

## Problem 12 — Audit Trail, Safety, Finish Harness

Prompt typed:

“Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, think of some safey rules for the agent show me what you'll put in prompts/prompt.md”

Follow-up prompt:

“Finish output/harness.md so it is clear how the system wroks. Model fields in models.py and why you chose them, Tools and abilities, safety rules, specs (loop limits, result caps, models, how to run front + back)”

What was lacking after the first prompt:

The first pass built the audit trail and only proposed the safety rules; they still had to be written into `prompts/prompt.md`, tested against the live agent (which showed sensitive data being logged, so redaction was added), and `output/harness.md` still had empty Models and Specs sections.

## Problem 13 — Push to GitHub and Submit the URL

Prompt typed:

“Problem 13: Push to Github and submit the URL” (with screenshots of the required `hw4/` file layout, the local-only data pack, and the README / `.env.example` / `.gitignore` rules)

Follow-up prompt:

“Can you do whatever needs to be done for me?”

What was lacking after the first prompt:

The first pass prepared and committed the repo (layout, README, `.env.example`, `.gitignore`, secret scan) but could not push because GitHub wasn't set up on this computer; the follow-up had the vibe coder install the official GitHub CLI, run a browser sign-in that I approved myself, create the public `hw4` repo, and push.

Repo URL: https://github.com/nnwokorie/hw4
