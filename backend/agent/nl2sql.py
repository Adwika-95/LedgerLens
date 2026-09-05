import os
import time
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv

from backend.database.db import DB_PATH
from backend.agent.rules import SCHEMA_DESCRIPTION, STATUS_VOCAB, FORMULAS
from backend.agent.validator import validate_sql, UnsafeQueryError

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_status_vocab_lines = "\n".join(f'- "{k}" -> {v}' for k, v in STATUS_VOCAB.items())

SQL_SYSTEM_PROMPT = f"""You are a B2B fintech reconciliation analyst who writes SQLite queries.

Schema:
{SCHEMA_DESCRIPTION}

Financial formulas already computed in the table (do not recompute them, just filter/aggregate):
{FORMULAS}

When the user uses everyday ops language, map it using this vocabulary:
{_status_vocab_lines}

Rules:
- Output ONLY one valid SQLite SELECT statement. No markdown fences, no commentary.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, ATTACH, PRAGMA, or CREATE.
- Never chain multiple statements with a semicolon.
- If the question can't be answered from this schema, output exactly:
  SELECT 'UNSUPPORTED_QUERY' AS error;
"""

EXPLAIN_SYSTEM_PROMPT = """You are a financial operations analyst explaining reconciliation query results
to a merchant finance team. You will receive the user's question and the raw database rows.
Explain the results in 2-3 concise, professional sentences. Lead with the financial impact
(amounts, counts, delta) rather than restating the question. Never invent numbers that
aren't in the rows. If the rows are empty, say plainly that nothing matched."""

sql_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
explain_model = genai.GenerativeModel(model_name="gemini-2.5-flash")


def process_finance_query(user_question: str) -> dict:
    full_sql_prompt = f"{SQL_SYSTEM_PROMPT}\n\nUser question: {user_question}\nSQL:"
    sql_response = sql_model.generate_content(full_sql_prompt)
    raw_sql = sql_response.text.strip().replace("```sql", "").replace("```", "").strip()

    try:
        safe_sql = validate_sql(raw_sql)
    except UnsafeQueryError as e:
        return {"error": str(e), "sql": raw_sql}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    start = time.perf_counter()
    try:
        cur = conn.cursor()
        cur.execute(safe_sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        return {"error": str(e), "sql": safe_sql}
    finally:
        conn.close()
    execution_time_ms = round((time.perf_counter() - start) * 1000, 2)

    full_explain_prompt = (
        f"{EXPLAIN_SYSTEM_PROMPT}\n\nUser question: {user_question}\n"
        f"Database rows ({len(rows)} total): {rows[:25]}\nExplanation:"
    )
    explanation_response = explain_model.generate_content(full_explain_prompt)
    explanation = explanation_response.text.strip()

    return {
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "explanation": explanation,
        "execution_time_ms": execution_time_ms,
    }
