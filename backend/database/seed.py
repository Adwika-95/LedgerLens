import random
import json
import os
from datetime import datetime, timedelta

from backend.database.db import init_db, get_connection

GROUND_TRUTH_PATH = os.path.join(os.path.dirname(__file__), "ground_truth.json")


def seed_database():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    random.seed(42)
    base_date = datetime(2026, 8, 1)

    products = [
        ("Cloud SaaS Subscription", 4999.00),
        ("Developer API Pack", 12000.00),
        ("Enterprise Gateway License", 45000.00),
        ("Analytics Add-on", 2500.00),
        ("Support Retainer", 15000.00),
    ]

    orders = []
    for i in range(1, 101):
        order_id = f"ORD_{i:04d}"
        cust_id = f"CUST_{random.randint(100, 999)}"
        prod_name, prod_price = random.choice(products)
        order_date = (base_date + timedelta(days=i % 25)).strftime("%Y-%m-%d")
        orders.append((order_id, order_date, cust_id, prod_name, prod_price, "INR", "PAID"))

    cur.executemany("INSERT INTO merchant_orders VALUES (?,?,?,?,?,?,?)", orders)

    # Deterministic ground truth: exactly which orders are broken, and why.
    # This is what lets the engine's output be *scored* instead of eyeballed.
    missing_gateway_idx = {5, 12}
    missing_bank_idx = {18, 27, 44}
    amount_mismatch_idx = {53, 71}
    duplicate_utr_idx = 89
    status_mismatch_idx = {33, 62}

    ground_truth = {}
    for i in missing_gateway_idx:
        ground_truth[f"ORD_{i:04d}"] = "MISSING_FROM_GATEWAY"
    for i in missing_bank_idx:
        ground_truth[f"ORD_{i:04d}"] = "MISSING_FROM_BANK"
    for i in amount_mismatch_idx:
        ground_truth[f"ORD_{i:04d}"] = "AMOUNT_MISMATCH"
    # Reusing a UTR makes BOTH the original order and the order that reused it
    # genuinely ambiguous from the bank statement's point of view — both are
    # real exceptions, not just the one whose UTR got overwritten.
    ground_truth[f"ORD_{duplicate_utr_idx:04d}"] = "DUPLICATE_UTR"
    ground_truth[f"ORD_{duplicate_utr_idx - 1:04d}"] = "DUPLICATE_UTR"
    for i in status_mismatch_idx:
        ground_truth[f"ORD_{i:04d}"] = "STATUS_MISMATCH"

    with open(GROUND_TRUTH_PATH, "w") as f:
        json.dump(ground_truth, f, indent=2)

    gateway_records = []
    bank_records = []

    for i in range(1, 101):
        order_id = f"ORD_{i:04d}"
        amount = orders[i - 1][4]
        tx_date = orders[i - 1][1]

        if i in missing_gateway_idx:
            continue

        payment_id = f"PAY_{i:04d}"
        utr = f"UTR_2026_{i:04d}"

        if i == duplicate_utr_idx:
            utr = f"UTR_2026_{duplicate_utr_idx - 1:04d}"

        fee = round(amount * 0.02, 2)
        tax = round(fee * 0.18, 2)
        net_expected = round(amount - fee - tax, 2)
        gw_status = "CAPTURED" if i not in status_mismatch_idx else "FAILED"

        gateway_records.append((
            payment_id, order_id, utr, tx_date,
            amount, fee, tax, net_expected, gw_status
        ))

        if i in missing_bank_idx or i in status_mismatch_idx:
            # A failed gateway payment never reaches settlement either.
            continue

        bank_tx_id = f"BANK_{i:04d}"
        settle_date = (datetime.strptime(tx_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
        bank_amount = net_expected

        if i == 53:
            bank_amount = round(net_expected - 182.00, 2)
        elif i == 71:
            bank_amount = round(net_expected - 500.00, 2)

        bank_records.append((
            bank_tx_id, utr, settle_date, bank_amount,
            f"REF_SETTLE_{i:04d}", "CREDITED"
        ))

    cur.executemany("INSERT INTO gateway_ledgers VALUES (?,?,?,?,?,?,?,?,?)", gateway_records)
    cur.executemany("INSERT INTO bank_statements VALUES (?,?,?,?,?,?)", bank_records)

    conn.commit()
    conn.close()
    print(f"Database seeded: 100 orders, {len(gateway_records)} gateway txns, {len(bank_records)} bank entries.")
    print(f"Ground truth written to {GROUND_TRUTH_PATH} ({len(ground_truth)} injected anomalies).")


if __name__ == "__main__":
    seed_database()
