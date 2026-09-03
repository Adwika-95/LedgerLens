import random
from datetime import datetime, timedelta
from db import init_db, get_connection

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

    missing_gateway_idx = {5, 12}        
    missing_bank_idx = {18, 27, 44}      
    amount_mismatch_idx = {53, 71}       
    duplicate_utr_idx = 89               

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

        gateway_records.append((
            payment_id, order_id, utr, tx_date,
            amount, fee, tax, net_expected, "CAPTURED"
        ))

        if i in missing_bank_idx:
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
    print("Database seeded successfully: 100 Orders, 98 Gateway Txns, 95 Bank Entries.")

if __name__ == "__main__":
    seed_database()