# AI Finance Controller

Built for Razorpay AI Builder Internship — Track 4 (AI Finance Controller).

A merchant reconciliation ledger: it closes the loop between an internal order,
what the payment gateway captured, and what actually landed in the bank
account — flags every mismatch, and lets you ask the ledger questions in
plain English.

## Why this exists (the finance-ops problem)

A merchant's order, its gateway capture, and its bank settlement are three
separate records that should agree and often don't: a payment never reaches
the bank, a UTR gets reused, a settlement is short by a few hundred rupees
after fees. Someone on a finance team currently checks this by hand across
three spreadsheets. This closes that loop automatically and tells you exactly
which records it *couldn't* resolve, instead of a dashboard that only shows
the good news.

## Architecture

```
backend/
  database/
    db.py        — schema + connection
    seed.py       — 100 synthetic B2B orders with 11 deliberately injected
                    anomalies, and the ground truth for scoring them
  reconciliation/
    engine.py     — the actual matching logic (order → gateway → bank)
    eval.py        — scores the engine against the injected ground truth
  agent/
    rules.py      — schema description, financial formulas, ops vocabulary
    validator.py  — AST-based SQL safety check (see "safety" below)
    nl2sql.py     — NL question -> SQL -> execute -> plain-English answer
  main.py         — FastAPI routes

frontend/
  src/App.jsx + components/ — the dashboard
```

## Running it

**Backend** — run every command below from the repo root (not from inside `backend/`),
because the modules import each other as `backend.database.db` etc.
```bash
cd finance-controller
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # add your GEMINI_API_KEY
python -m backend.database.seed          # builds finance_controller.db + ground_truth.json
python -m backend.reconciliation.engine  # runs the first reconciliation batch
uvicorn backend.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Score the engine's accuracy** (do this — it's the number you'll be asked about):
```bash
python -m backend.reconciliation.eval
```

## What changed from the original prototype, and why

This project went through three prior forms — a generic e-commerce NL2SQL
demo, then a first fintech pivot — before this version. Three things were
broken or missing in that hand-off, worth knowing if asked:

1. **The reconciliation engine was never wired to the API.** `engine.py`
   existed but nothing called it — the dashboard could only ever show
   whatever was already sitting in the database. Added
   `POST /api/reconciliation/run` so a batch can actually be triggered.

2. **SQL safety was a keyword substring check.** `"drop" in sql.lower()`
   can't tell a safe query with "update" in a quoted string from an unsafe
   one, and it doesn't stop statement chaining
   (`SELECT 1; DROP TABLE reconciliation_results;` sails straight through a
   substring check). `validator.py` now parses the SQL into an AST with
   `sqlglot` and rejects anything that isn't a single, in-schema `SELECT` —
   tested against chaining, DML, and unknown-table attempts.

3. **Accuracy was asserted, never measured.** The track's own bar says "one
   cherry-picked match proves nothing." `seed.py` now writes out exactly
   which 11 orders it deliberately broke and how; `eval.py` scores the
   engine's output against that ground truth. Current numbers on the
   seeded batch: **100% recall, 100% precision** on the 11 injected
   anomalies, 89% overall match rate on the batch. Re-run `eval.py`
   yourself — don't take the number on faith, and don't say this in an
   interview without having actually reproduced it.

## Design decisions worth being able to explain

- **Why sqlglot over a bigger safety net (e.g. a full SQL firewall)?**
  The threat model here is a probabilistic SQL generator making a mistake,
  not an adversarial user with API access — the FastAPI layer accepts free
  text, but there's no auth in front of it, so treat this as a portfolio /
  hackathon demo, not something to point at a real merchant database without
  adding auth first. An AST allow-list of one SELECT statement over known
  tables is enough for that threat model and is easy to defend line by line.

- **Why keep the keyword-based reconciliation engine instead of an LLM
  doing the matching?** Reconciliation is deterministic bookkeeping — order
  → gateway → bank, checked in a fixed sequence — and a rules engine gives
  you 100% reproducible, auditable output. The LLM's job is the *query*
  layer on top, where natural language genuinely varies. Mixing them would
  make the core financial logic non-deterministic for no benefit.

- **Why a plain query box instead of a full chat UI?** The exceptions table
  is the actual job — a finance controller's day is spent triaging that
  list, not chatting with a bot. The NL2SQL feature is real and useful for
  ad hoc questions, but it's a secondary panel, not the whole product.

## Known limitations (say these before someone else finds them)

- Single fixed schema — no dynamic upload of a merchant's own ledger format.
- No auth on the API; not production-ready as-is.
- The "explain" pass sends up to 25 rows to Gemini per question — fine for a
  demo, would need pagination/summarization for large result sets.
- Currency is INR-only; no multi-currency settlement logic.
