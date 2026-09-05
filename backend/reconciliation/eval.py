"""
Scores the reconciliation engine against the known-injected anomalies from seed.py.
Run after seeding + running a batch:
    python -m backend.database.seed
    python -m backend.reconciliation.engine
    python -m backend.reconciliation.eval

This is what turns "the demo looked right" into a number you can defend in an
interview: precision/recall on a held-out set of deliberately broken records,
not a single cherry-picked example.
"""
import json
import os

from backend.database.db import get_connection

GROUND_TRUTH_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "ground_truth.json")


def evaluate():
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)  # {order_id: expected_status}

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT order_id, reconciliation_status FROM reconciliation_results")
    predicted = {row["order_id"]: row["reconciliation_status"] for row in cur.fetchall()}
    conn.close()

    true_positives = 0   # flagged as an exception, and it genuinely was one, with the right reason
    wrong_reason = 0      # flagged as *some* exception, but the wrong category
    false_negatives = 0   # a genuine exception the engine called MATCHED (the dangerous failure mode)
    false_positives = 0   # a genuinely clean record the engine flagged as broken

    for order_id, expected_status in ground_truth.items():
        actual_status = predicted.get(order_id, "MISSING_FROM_RESULTS")
        if actual_status == expected_status:
            true_positives += 1
        elif actual_status == "MATCHED":
            false_negatives += 1
        else:
            wrong_reason += 1

    clean_orders = [oid for oid in predicted if oid not in ground_truth]
    for order_id in clean_orders:
        if predicted[order_id] != "MATCHED":
            false_positives += 1

    total_injected = len(ground_truth)
    recall = true_positives / total_injected if total_injected else 0
    precision = true_positives / (true_positives + false_positives + wrong_reason) if (true_positives + false_positives + wrong_reason) else 0

    print("Reconciliation engine — held-out accuracy")
    print(f"  Injected anomalies       : {total_injected}")
    print(f"  Correctly caught + typed : {true_positives}")
    print(f"  Caught, wrong category   : {wrong_reason}")
    print(f"  Missed entirely (FN)     : {false_negatives}")
    print(f"  False alarms on clean rows (FP): {false_positives}")
    print(f"  Recall    : {recall * 100:.1f}%")
    print(f"  Precision : {precision * 100:.1f}%")

    return {
        "injected": total_injected,
        "true_positives": true_positives,
        "wrong_reason": wrong_reason,
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "recall_pct": round(recall * 100, 1),
        "precision_pct": round(precision * 100, 1),
    }


if __name__ == "__main__":
    evaluate()
