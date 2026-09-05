AI Finance Controller
Built for Razorpay AI Builder Internship — Track 4 (AI Finance Controller).

A merchant reconciliation ledger: it closes the loop between an internal order, what the payment gateway captured, and what actually landed in the bank account — flags every mismatch, and lets you ask the ledger questions in plain English.

Why We Built This
In finance operations, an order, its gateway capture, and the bank settlement are three different records that should match, but often don't. Sometimes a payment never reaches the bank, a UTR gets reused, or a settlement is short because of hidden fees. Right now, finance teams manually check this across three messy spreadsheets.

This project automates that entire loop. Instead of showing a fake dashboard where everything looks good, it points out exactly which records failed to resolve and why.

Project Structure
backend/
  database/
    db.py — database schema and connection
    seed.py — 100 synthetic B2B orders with 11 intentional anomalies + ground truth for testing
  reconciliation/
    engine.py — the matching logic (order to gateway to bank)
    eval.py — grades the engine against the injected errors
  agent/
    rules.py — schema descriptions, financial formulas, and ops terms
    validator.py — AST-based SQL safety checks (prevents bad queries)
    nl2sql.py — converts your plain English questions into SQL and explains the result
  main.py — FastAPI server routes

frontend/
  src/App.jsx and components — the dashboard UI
How to Run It Locally
Make sure you run these backend commands from the repo root folder, not inside the backend folder, otherwise the python module imports will break.

Backend Setup
cd finance-controller
python -m venv venv 
source venv/bin/activate   # Use venv\Scripts�ctivate on Windows
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # Don't forget to put your GEMINI_API_KEY here
python -m backend.database.seed          # Creates the SQLite db and ground truth file
python -m backend.reconciliation.engine  # Runs the first batch of reconciliations
uvicorn backend.main:app --reload --port 8000
Frontend Setup
cd frontend
npm install
npm run dev
Check the Accuracy Score
Don't skip this part, because people will ask you about it during reviews:

python -m backend.reconciliation.eval
What We Fixed From the First Try
We went through a couple of failed prototypes before landing on this one. Here are three major fixes we made:

The engine was disconnected: engine.py existed, but nothing in the API actually called it. The dashboard was just showing whatever dummy data was already sitting in the database. We added a proper POST /api/reconciliation/run route so you can trigger a batch from the app.
SQL safety was weak: Originally, it just checked if the word "drop" was in the query using a basic string search. That is super easy to bypass with statement chaining or special characters. We swapped it out for sqlglot to parse the SQL into an Abstract Syntax Tree (AST), making sure it only accepts a single, safe SELECT statement over our exact tables.
Accuracy was just a guess: People love to claim high accuracy without proof. Now, seed.py tracks the exact 11 records it messed up, and eval.py scores our engine against that answer key. On our seeded batches, we get 100 percent precision and recall on the anomalies, and an 89 percent overall match rate.
Design Choices We Made
Why use sqlglot instead of a heavy SQL firewall? Our main threat here is the AI accidentally generating a weird or broken query, not a hacker trying to attack us. Since there is no user login yet, this is meant as a portfolio/hackathon demo. An AST filter that only allows one SELECT statement on our known tables is lightweight and easy to defend.
Why keep the reconciliation logic as code instead of letting an LLM do it? Reconciliation is strict bookkeeping—order to gateway to bank in a specific order. Writing it in rules gives us 100 percent consistent and auditable results. We only use the LLM for the search/query layer where natural language is actually required.
Why a simple query box instead of a chatbot? Finance workers don't want to chat with a bot all day; their actual job is fixing the exceptions table. The NL2SQL search bar is helpful for quick ad-hoc questions, but it stays out of the way of the main workflow.
Known Limitations
It only supports one fixed schema right now—you can't upload your own custom company ledger formats yet.
There is no user authentication on the API, so it is not ready for production use out of the box.
The explanation feature sends up to 25 rows to Gemini per question, which works fine for a demo, but would need pagination for massive datasets.
Everything is hardcoded to Indian Rupees (INR); there is no multi-currency logic yet.
