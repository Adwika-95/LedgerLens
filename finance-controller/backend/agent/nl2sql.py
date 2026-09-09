import os
import time
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from backend.database.db import DB_PATH
from backend.agent.rules import SCHEMA_DESCRIPTION, STATUS_VOCAB, FORMULAS
from backend.agent.validator import validate_sql, UnsafeQueryError


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

# Project structure:
#
# finance-controller/
# ├── .env
# ├── backend/
# │   ├── main.py
# │   └── agent/
# │       └── nl2sql.py
#
# From nl2sql.py:
# parent        = agent
# parent.parent = backend
# parent.parent.parent = finance-controller

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

load_dotenv(dotenv_path=_ENV_PATH)

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not _GEMINI_API_KEY:
    raise RuntimeError(
        f"GEMINI_API_KEY is not set.\n"
        f"Expected .env file at: {_ENV_PATH}\n"
        f"Add:\n"
        f"GEMINI_API_KEY=your_real_key_here"
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(api_key=_GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# BUILD STATUS VOCABULARY
# ============================================================

_status_vocab_lines = "\n".join(
    f'- "{key}" -> {value}'
    for key, value in STATUS_VOCAB.items()
)


# ============================================================
# SQL GENERATION PROMPT
# ============================================================

SQL_SYSTEM_PROMPT = f"""
You are a B2B fintech reconciliation analyst who writes SQLite queries.

DATABASE SCHEMA:
{SCHEMA_DESCRIPTION}

FINANCIAL FORMULAS:
{FORMULAS}

Use these formulas when answering financial questions.
Do not invent formulas that are not supported by the schema.

STATUS VOCABULARY:
{_status_vocab_lines}

RULES:

1. Output ONLY one valid SQLite SELECT statement.
2. Do not use markdown.
3. Do not use ```sql fences.
4. Never use:
   DROP
   DELETE
   UPDATE
   INSERT
   ALTER
   ATTACH
   PRAGMA
   CREATE
5. Never generate multiple SQL statements.
6. Do not put a semicolon in the middle of the query.
7. Only query tables and columns that exist in the provided schema.
8. Prefer simple, reliable SQLite syntax.
9. If the question cannot be answered from this database schema,
   output exactly:

   SELECT 'UNSUPPORTED_QUERY' AS error;

10. Do not modify the database in any way.
"""


# ============================================================
# EXPLANATION PROMPT
# ============================================================

EXPLAIN_SYSTEM_PROMPT = """
You are a financial operations analyst explaining reconciliation
query results to a merchant finance team.

You will receive:
- The user's question
- The raw database rows returned by the SQL query

Explain the result in 2-3 concise and professional sentences.

Rules:
1. Lead with the financial impact, amount, count, discrepancy, or
   other important result.
2. Do not simply repeat the user's question.
3. Never invent numbers.
4. Only use information present in the database rows.
5. If no rows were returned, clearly state that nothing matched.
6. Keep the explanation easy for a finance team to understand.
"""


# ============================================================
# GEMINI HELPER
# ============================================================

def generate_text(prompt: str) -> str:
    """
    Sends a prompt to Gemini and returns the generated text.
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()


# ============================================================
# MAIN FINANCE QUERY PIPELINE
# ============================================================

def process_finance_query(user_question: str) -> dict:
    """
    Complete finance query pipeline:

    User question
        ↓
    Gemini
        ↓
    SQL
        ↓
    SQL validation
        ↓
    SQLite execution
        ↓
    Gemini explanation
        ↓
    JSON response
    """

    if not user_question or not user_question.strip():
        return {
            "error": "Question cannot be empty."
        }

    user_question = user_question.strip()

    # --------------------------------------------------------
    # STEP 1: Generate SQL
    # --------------------------------------------------------

    full_sql_prompt = (
        f"{SQL_SYSTEM_PROMPT}\n\n"
        f"USER QUESTION:\n{user_question}\n\n"
        f"SQL:"
    )

    raw_sql = generate_text(full_sql_prompt)

    # Remove accidental markdown fences if Gemini returns them
    raw_sql = (
        raw_sql
        .replace("```sql", "")
        .replace("```sqlite", "")
        .replace("```", "")
        .strip()
    )

    # --------------------------------------------------------
    # STEP 2: Validate SQL
    # --------------------------------------------------------

    try:
        safe_sql = validate_sql(raw_sql)

    except UnsafeQueryError as e:
        return {
            "error": str(e),
            "sql": raw_sql
        }

    # --------------------------------------------------------
    # STEP 3: Execute SQL
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    start = time.perf_counter()

    try:
        cursor = conn.cursor()

        cursor.execute(safe_sql)

        columns = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )

        rows = [
            dict(row)
            for row in cursor.fetchall()
        ]

    except Exception as e:
        return {
            "error": f"SQL execution error: {str(e)}",
            "sql": safe_sql
        }

    finally:
        conn.close()

    execution_time_ms = round(
        (time.perf_counter() - start) * 1000,
        2
    )

    # --------------------------------------------------------
    # STEP 4: Generate Human Explanation
    # --------------------------------------------------------

    full_explain_prompt = (
        f"{EXPLAIN_SYSTEM_PROMPT}\n\n"
        f"USER QUESTION:\n{user_question}\n\n"
        f"DATABASE ROWS ({len(rows)} total):\n"
        f"{rows[:25]}\n\n"
        f"EXPLANATION:"
    )

    explanation = generate_text(full_explain_prompt)

    # --------------------------------------------------------
    # STEP 5: Return Result
    # --------------------------------------------------------

    return {
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "explanation": explanation,
        "execution_time_ms": execution_time_ms
    }