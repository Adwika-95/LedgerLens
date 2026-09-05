import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "finance_controller.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS reconciliation_results;
    DROP TABLE IF EXISTS bank_statements;
    DROP TABLE IF EXISTS gateway_ledgers;
    DROP TABLE IF EXISTS merchant_orders;

    CREATE TABLE merchant_orders (
        order_id TEXT PRIMARY KEY,
        order_date TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        product TEXT NOT NULL,
        order_amount REAL NOT NULL,
        currency TEXT DEFAULT 'INR',
        order_status TEXT NOT NULL
    );

    CREATE TABLE gateway_ledgers (
        payment_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        utr TEXT,
        transaction_date TEXT NOT NULL,
        gateway_amount REAL NOT NULL,
        gateway_fee REAL NOT NULL,
        tax_on_fee REAL NOT NULL,
        net_settlement_amount REAL NOT NULL,
        payment_status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES merchant_orders(order_id)
    );

    CREATE TABLE bank_statements (
        bank_transaction_id TEXT PRIMARY KEY,
        utr TEXT NOT NULL,
        settlement_date TEXT NOT NULL,
        bank_amount REAL NOT NULL,
        bank_reference TEXT NOT NULL,
        bank_status TEXT NOT NULL
    );

    CREATE TABLE reconciliation_results (
        reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        payment_id TEXT,
        utr TEXT,
        order_amount REAL,
        gateway_amount REAL,
        gateway_fee REAL,
        tax_on_fee REAL,
        expected_settlement REAL,
        actual_bank_amount REAL,
        discrepancy REAL,
        reconciliation_status TEXT NOT NULL,
        exception_reason TEXT,
        processed_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()
