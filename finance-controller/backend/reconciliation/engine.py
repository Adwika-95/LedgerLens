from datetime import datetime

from backend.database.db import get_connection


def run_reconciliation_batch():
    conn = get_connection()
    cur = conn.cursor()

    # Clear previous results before running a new batch
    cur.execute("DELETE FROM reconciliation_results")

    cur.execute("SELECT * FROM merchant_orders")
    orders = cur.fetchall()

    metrics = {
        "total_processed": 0,
        "matched": 0,
        "exceptions": 0,
        "missing_from_gateway": 0,
        "missing_from_bank": 0,
        "amount_mismatch": 0,
        "duplicate_utr": 0,
        "status_mismatch": 0,
    }

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results_to_insert = []

    for order in orders:
        order_id = order["order_id"]
        order_amount = order["order_amount"]
        metrics["total_processed"] += 1

        payment_id, utr, gateway_amt, fee, tax = None, None, None, None, None
        expected_settlement, actual_bank_amt, diff = None, None, None
        status = "UNRESOLVED"
        reason = ""

        cur.execute("SELECT * FROM gateway_ledgers WHERE order_id = ?", (order_id,))
        gateway_records = cur.fetchall()

        if len(gateway_records) == 0:
            status = "MISSING_FROM_GATEWAY"
            reason = f"Order {order_id} not found in gateway ledgers."
            metrics["missing_from_gateway"] += 1
            metrics["exceptions"] += 1
        else:
            gw = gateway_records[0]
            payment_id = gw["payment_id"]
            utr = gw["utr"]
            gateway_amt = gw["gateway_amount"]
            fee = gw["gateway_fee"]
            tax = gw["tax_on_fee"]
            expected_settlement = gw["net_settlement_amount"]
            gw_status = gw["payment_status"]

            if gw_status != "CAPTURED":
                status = "STATUS_MISMATCH"
                reason = f"Gateway status is {gw_status}, expected CAPTURED."
                metrics["status_mismatch"] += 1
                metrics["exceptions"] += 1
            else:
                cur.execute("SELECT * FROM bank_statements WHERE utr = ?", (utr,))
                bank_records = cur.fetchall()

                if len(bank_records) == 0:
                    status = "MISSING_FROM_BANK"
                    reason = f"UTR {utr} not found in bank statements."
                    metrics["missing_from_bank"] += 1
                    metrics["exceptions"] += 1
                elif len(bank_records) > 1:
                    status = "DUPLICATE_UTR"
                    reason = f"Multiple bank entries found for UTR {utr}."
                    metrics["duplicate_utr"] += 1
                    metrics["exceptions"] += 1
                else:
                    bank = bank_records[0]
                    actual_bank_amt = bank["bank_amount"]
                    diff = round(expected_settlement - actual_bank_amt, 2)

                    if abs(diff) > 0.01:
                        status = "AMOUNT_MISMATCH"
                        reason = f"Expected {expected_settlement}, bank settled {actual_bank_amt}. Diff: {diff}"
                        metrics["amount_mismatch"] += 1
                        metrics["exceptions"] += 1
                    else:
                        status = "MATCHED"
                        reason = "Fully reconciled."
                        metrics["matched"] += 1

        results_to_insert.append((
            order_id, payment_id, utr, order_amount, gateway_amt,
            fee, tax, expected_settlement, actual_bank_amt, diff,
            status, reason, timestamp,
        ))

    cur.executemany("""
        INSERT INTO reconciliation_results (
            order_id, payment_id, utr, order_amount, gateway_amount,
            gateway_fee, tax_on_fee, expected_settlement, actual_bank_amount,
            discrepancy, reconciliation_status, exception_reason, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, results_to_insert)

    conn.commit()
    conn.close()

    match_rate = (metrics["matched"] / metrics["total_processed"]) * 100 if metrics["total_processed"] > 0 else 0
    metrics["match_rate_percentage"] = round(match_rate, 2)
    metrics["run_at"] = timestamp

    return metrics


if __name__ == "__main__":
    print("Running batch reconciliation...")
    results = run_reconciliation_batch()
    print(f"Processed: {results['total_processed']}")
    print(f"Matched: {results['matched']}")
    print(f"Exceptions: {results['exceptions']}")
    print(f"Match Rate: {results['match_rate_percentage']}%")
