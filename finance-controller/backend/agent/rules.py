"""
Domain rules for the finance agent, kept separate from the prompt-building code
in nl2sql.py so they can be read, reviewed, and extended on their own — this is
the "financial domain grounding" the track brief asks for.
"""

SCHEMA_DESCRIPTION = """
Table: reconciliation_results
Columns:
- order_id (TEXT)               merchant order identifier, e.g. ORD_0053
- payment_id (TEXT)             gateway payment identifier, e.g. PAY_0053
- utr (TEXT)                    bank UTR / settlement reference
- order_amount (REAL)           amount the merchant's order was placed for
- gateway_amount (REAL)         amount captured by the payment gateway
- gateway_fee (REAL)            gateway's processing fee
- tax_on_fee (REAL)             GST charged on the gateway fee (18%)
- expected_settlement (REAL)    what should have reached the merchant's bank account
                                 = gateway_amount - gateway_fee - tax_on_fee
- actual_bank_amount (REAL)     what the bank statement actually shows
- discrepancy (REAL)            expected_settlement - actual_bank_amount
- reconciliation_status (TEXT)  one of: MATCHED, MISSING_FROM_GATEWAY,
                                 MISSING_FROM_BANK, AMOUNT_MISMATCH,
                                 DUPLICATE_UTR, STATUS_MISMATCH
- exception_reason (TEXT)       human-readable explanation of the status
- processed_at (TEXT)           when this batch reconciliation ran
"""

# Vocabulary a finance ops person actually uses, mapped to the columns/values
# that answer it. Not exhaustive — extend as real query logs reveal gaps.
STATUS_VOCAB = {
    "failed": "STATUS_MISMATCH",
    "disputed": "AMOUNT_MISMATCH",
    "settled": "MATCHED",
    "unsettled": "reconciliation_status != 'MATCHED'",
    "duplicate": "DUPLICATE_UTR",
    "stuck": "MISSING_FROM_BANK",
    "not captured": "MISSING_FROM_GATEWAY",
}

FORMULAS = """
Net settlement = gateway_amount - gateway_fee - tax_on_fee
Discrepancy    = expected_settlement - actual_bank_amount (positive = merchant was underpaid)
Match rate     = matched_count / total_processed
"""
