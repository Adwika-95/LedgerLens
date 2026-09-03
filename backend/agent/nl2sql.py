import os
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
from backend.database.db import DB_PATH

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SCHEMA = """
Table: reconciliation_results
Columns:
- order_id (TEXT)
- payment_id (TEXT)
- utr (TEXT)
- order_amount (REAL)
- gateway_amount (REAL)
- gateway_fee (REAL)
- tax_on_fee (REAL)
- expected_settlement (REAL)
- actual_bank_amount (REAL)
- discrepancy (REAL)
- reconciliation_status (TEXT: 'MATCHED', 'MISSING_FROM_GATEWAY', 'MISSING_FROM_BANK', 'AMOUNT_MISMATCH', 'DUPLICATE_UTR', 'STATUS_MISMATCH')
- exception_reason (TEXT)
- processed_at (TEXT)
"""

SQL_SYSTEM_PROMPT = f"""You are an AI Finance Controller.
Generate ONLY a valid SQLite SELECT query based on this schema:
{SCHEMA}

Rules:
- NEVER output markdown formatting (like ```sql or ```). Output raw SQL only.
- ONLY use SELECT queries. Never use DROP, DELETE, UPDATE, INSERT, ALTER, ATTACH, or PRAGMA.
- If asking for a specific UTR or Order ID, filter with a WHERE clause.
"""

EXPLAIN_SYSTEM_PROMPT = """You are a financial operations expert explaining reconciliation data.
You will receive the user's question and the raw database results.
Explain the results clearly and professionally in 2-3 concise sentences. Focus on the financial impact, delta discrepancies, or reconciliation root causes. Do not invent facts or numbers. If the results are empty, state that no matching records were found."""

# Initialize base models without system_instruction parameter
sql_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
explain_model = genai.GenerativeModel(model_name="gemini-2.5-flash")

def is_safe_query(sql: str) -> bool:
    forbidden = ["drop", "delete", "update", "insert", "alter", "attach", "pragma", "commit"]
    return not any(word in sql.lower() for word in forbidden)

def process_finance_query(user_question: str):
    # Pass 1: Generate SQL (prepend system instructions)
    full_sql_prompt = f"{SQL_SYSTEM_PROMPT}\n\nUser Question: {user_question}\nSQL Query:"
    sql_response = sql_model.generate_content(full_sql_prompt)
    sql = sql_response.text.strip().replace("```sql", "").replace("```", "").strip()
    
    if not is_safe_query(sql):
        return {"error": "Unsafe SQL detected — query execution blocked.", "sql": sql}
        
    # Pass 2: Execute query against SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        return {"error": str(e), "sql": sql}
    finally:
        conn.close()

    # Pass 3: Synthesize financial explanation
    full_explain_prompt = f"{EXPLAIN_SYSTEM_PROMPT}\n\nUser Question: {user_question}\nDatabase Results: {rows}\nExplanation:"
    explanation_response = explain_model.generate_content(full_explain_prompt)
    explanation = explanation_response.text.strip()

    return {
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "explanation": explanation
    }