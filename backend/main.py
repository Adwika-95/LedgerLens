from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

from backend.agent.nl2sql import process_finance_query
from backend.database.db import DB_PATH
from backend.reconciliation.engine import run_reconciliation_batch

app = FastAPI(title="AI Finance Controller API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class ChatRequest(BaseModel):
    question: str


@app.post("/api/reconciliation/run")
def trigger_reconciliation():
    """Runs a fresh reconciliation batch over the current merchant_orders /
    gateway_ledgers / bank_statements tables. This is the step the previous
    version of the API never exposed — the dashboard could only ever show
    whatever was already sitting in reconciliation_results."""
    try:
        metrics = run_reconciliation_batch()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reconciliation/summary")
def get_summary():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as total FROM reconciliation_results")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as matched FROM reconciliation_results WHERE reconciliation_status = 'MATCHED'")
        matched = cur.fetchone()["matched"]

        cur.execute("""
            SELECT reconciliation_status, COUNT(*) as count
            FROM reconciliation_results
            WHERE reconciliation_status != 'MATCHED'
            GROUP BY reconciliation_status
        """)
        breakdown = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT MAX(processed_at) as last_run FROM reconciliation_results")
        last_run_row = cur.fetchone()
        last_run = last_run_row["last_run"] if last_run_row else None

        exceptions = total - matched
        match_rate = round((matched / total) * 100, 2) if total > 0 else 0

        return {
            "total_transactions": total,
            "matched": matched,
            "exceptions": exceptions,
            "match_rate": match_rate,
            "breakdown": breakdown,
            "last_run": last_run,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/reconciliation/exceptions")
def get_exceptions():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, utr, expected_settlement, actual_bank_amount,
                   discrepancy, reconciliation_status, exception_reason
            FROM reconciliation_results
            WHERE reconciliation_status != 'MATCHED'
            ORDER BY order_id
        """)
        exceptions = [dict(row) for row in cur.fetchall()]
        return {"exceptions": exceptions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/api/chat")
def ask_finance_agent(request: ChatRequest):
    try:
        result = process_finance_query(request.question)
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
