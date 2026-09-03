from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

from backend.agent.nl2sql import process_finance_query
from backend.database.db import DB_PATH

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

@app.get("/api/reconciliation/summary")
def get_summary():
    """Returns aggregated KPI metrics for the overview cards."""
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
        
        exceptions = total - matched
        match_rate = round((matched / total) * 100, 2) if total > 0 else 0
        
        return {
            "total_transactions": total,
            "matched": matched,
            "exceptions": exceptions,
            "match_rate": match_rate,
            "breakdown": breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/reconciliation/exceptions")
def get_exceptions():
    """Returns the itemized list of failed reconciliation records."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, utr, expected_settlement, actual_bank_amount, 
                   discrepancy, reconciliation_status, exception_reason 
            FROM reconciliation_results 
            WHERE reconciliation_status != 'MATCHED'
        """)
        exceptions = [dict(row) for row in cur.fetchall()]
        return {"exceptions": exceptions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/chat")
def ask_finance_agent(request: ChatRequest):
    """Translates natural language questions to SQL and returns grounded explanations."""
    try:
        result = process_finance_query(request.question)
        if "error" in result and result.get("error"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))