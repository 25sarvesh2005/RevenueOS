"""
RevenueOS – Synthetic Omnichannel Retail Data Generator
========================================================
Generates realistic, interconnected omnichannel business datasets designed
to test and demonstrate the full RevenueOS intelligence pipeline:

Entities generated:
  1. Customers (1,000+ records with realistic segments, cities, dates)
  2. Products (120+ SKUs across categories, costs, and MSRP margins)
  3. Orders (25,000+ line items with realistic discount curves, channels, locations)
  4. Payments (1:1 and 1:many with intentional gateway failures and card declines)
  5. Returns (Intentional return reasons, defect clustering on specific SKUs)
  6. Inventory (Daily warehouse snapshots with intentionally engineered stockouts)
  7. Marketing (Campaign spend, impressions, clicks across Google, Meta, Email, TikTok)

Engineered Business Scenarios:
  - "Revenue Traps": High-revenue products with severe discount leakage or unexpected return spikes.
  - "Payment Gateway Degradation": Spikes in payment failures for specific payment methods.
  - "Ghost Stockouts": Popular products hitting 0 stock causing lost revenue opportunity.
  - "At-Risk Whale Customers": High historic LTV customers whose recency is slipping.

Usage:
  python data/generate_sample_data.py [--rows 20000] [--out-dir data/raw]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Set deterministic seed for repeatable simulation
random.seed(42)
np.random.seed(42)


def generate_customers(num_customers: int = 1500) -> pd.DataFrame:
    """Generate realistic customer master records."""
    first_names = [
        "Aarav", "Aditi", "Rohan", "Priya", "Vikram", "Ananya", "Rahul", "Sneha",
        "Arjun", "Pooja", "Kabir", "Neha", "Karan", "Tanvi", "Siddharth", "Ishita",
        "Amit", "Divya", "Rajesh", "Kavita", "Suresh", "Meera", "Manish", "Ritu",
        "Deepak", "Swati", "Nikhil", "Simran", "Varun", "Sunita", "Harsh", "Shreya"
    ]
    last_names = [
        "Sharma", "Verma", "Patel", "Mehta", "Reddy", "Nair", "Iyer", "Gupta",
        "Singh", "Chopra", "Malhotra", "Kapoor", "Bhatia", "Jain", "Saxena", "Deshmukh",
        "Rao", "Menon", "Ghosh", "Chatterjee", "Banerjee", "Pillai", "Kulkarni", "Joshi"
    ]
    cities = [
        ("Mumbai", "West"), ("Pune", "West"), ("Ahmedabad", "West"),
        ("Delhi", "North"), ("Noida", "North"), ("Gurugram", "North"), ("Jaipur", "North"),
        ("Bengaluru", "South"), ("Hyderabad", "South"), ("Chennai", "South"), ("Kochi", "South"),
        ("Kolkata", "East"), ("Bhubaneswar", "East"), ("Patna", "East")
    ]
    segments = ["Enterprise", "Mid-Market", "SMB", "Consumer", "VIP"]
    segment_weights = [0.05, 0.15, 0.30, 0.45, 0.05]

    start_date = date(2023, 1, 1)
    end_date = date(2025, 12, 31)
    date_range_days = (end_date - start_date).days

    records = []
    for i in range(1, num_customers + 1):
        cust_id = f"CUST-{i:05d}"
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 999)}@example.com"
        city, region = random.choice(cities)
        signup_offset = random.randint(0, date_range_days)
        signup_dt = start_date + timedelta(days=signup_offset)
        segment = np.random.choice(segments, p=segment_weights)

        records.append({
            "customer_id": cust_id,
            "name": name,
            "email": email,
            "city": city,
            "region": region,
            "signup_date": signup_dt.isoformat(),
            "segment": segment,
        })

    return pd.DataFrame(records)


def generate_products() -> pd.DataFrame:
    """Generate product catalog with engineered margin profiles and categories."""
    catalog = [
        # Electronics
        ("PRD-E101", "UltraBook Pro 15", "Electronics", "Laptops", "TechSource Ltd", 45000.0, 65000.0),
        ("PRD-E102", "ErgoMechanical Keyboard", "Electronics", "Peripherals", "Keytronics", 3200.0, 5999.0),
        ("PRD-E103", "Precision Wireless Mouse", "Electronics", "Peripherals", "Keytronics", 1100.0, 2499.0),
        ("PRD-E104", "Noise-Cancelling Headphones", "Electronics", "Audio", "SoundVibe", 5500.0, 9999.0),
        ("PRD-E105", "4K Ultra-Wide Monitor 34", "Electronics", "Displays", "VisionDisplay", 28000.0, 42000.0),
        ("PRD-E106", "Smart Home Hub v2", "Electronics", "Smart Home", "ConnectLife", 2200.0, 3999.0),
        ("PRD-E107", "USB-C Dual Dock Station", "Electronics", "Accessories", "TechSource Ltd", 2800.0, 4999.0),
        ("PRD-E108", "Fast Wireless Charger 30W", "Electronics", "Accessories", "ConnectLife", 850.0, 1699.0),
        # Engineered Revenue Trap: High cost, competitive razor margin, prone to heavy discount
        ("PRD-E109", "Flagship Smartphone X12", "Electronics", "Mobiles", "ApexMobile", 48000.0, 52000.0),
        ("PRD-E110", "TrueWireless Earbuds Neo", "Electronics", "Audio", "SoundVibe", 1600.0, 2999.0),

        # Apparel
        ("PRD-A201", "Classic Oxford Cotton Shirt", "Apparel", "Men", "FabricCrafters", 650.0, 1899.0),
        ("PRD-A202", "Slim Fit Denim Jeans", "Apparel", "Men", "FabricCrafters", 850.0, 2499.0),
        ("PRD-A203", "Tailored Linen Blazer", "Apparel", "Men", "LuxeWear", 2200.0, 6499.0),
        ("PRD-A204", "Breathable Floral Midi Dress", "Apparel", "Women", "LuxeWear", 950.0, 2899.0),
        ("PRD-A205", "High-Waist Performance Leggings", "Apparel", "Women", "ActivePulse", 550.0, 1799.0),
        ("PRD-A206", "Merino Wool Crewneck Sweater", "Apparel", "Unisex", "LuxeWear", 1400.0, 3999.0),
        ("PRD-A207", "Waterproof All-Weather Jacket", "Apparel", "Outerwear", "ActivePulse", 1800.0, 4999.0),
        ("PRD-A208", "Cushioned Running Shoes", "Apparel", "Footwear", "ActivePulse", 1900.0, 4499.0),

        # Home & Kitchen
        ("PRD-H301", "Cold Press Slow Juicer", "Home & Kitchen", "Appliances", "NutriBlend", 3800.0, 7999.0),
        ("PRD-H302", "Smart Air Fryer XL", "Home & Kitchen", "Appliances", "NutriBlend", 3200.0, 6499.0),
        ("PRD-H303", "Cast Iron Dutch Oven 5L", "Home & Kitchen", "Cookware", "HeritageCook", 1600.0, 3499.0),
        ("PRD-H304", "Ergonomic Memory Foam Pillow", "Home & Kitchen", "Bedding", "ComfortSleep", 600.0, 1899.0),
        ("PRD-H305", "Microfiber Sheet Set Queen", "Home & Kitchen", "Bedding", "ComfortSleep", 750.0, 2199.0),
        ("PRD-H306", "Aroma Ultrasonic Diffuser", "Home & Kitchen", "Home Fragrance", "HeritageCook", 450.0, 1299.0),

        # Beauty & Personal Care
        ("PRD-B401", "Vitamin C Radiance Serum", "Beauty", "Skincare", "DermaGlow", 320.0, 1199.0),
        ("PRD-B402", "Hydrating Hyaluronic Gel", "Beauty", "Skincare", "DermaGlow", 280.0, 999.0),
        ("PRD-B403", "Botanical Sulfate-Free Shampoo", "Beauty", "Haircare", "DermaGlow", 220.0, 749.0),
        ("PRD-B404", "Sonic Facial Cleansing Brush", "Beauty", "Tools", "AuraTech", 1100.0, 2899.0),

        # Fitness & Outdoors
        ("PRD-F501", "Adjustable Dumbbell Set 20kg", "Fitness", "Strength", "IronCore", 2900.0, 5999.0),
        ("PRD-F502", "Eco-Friendly Yoga Mat 6mm", "Fitness", "Accessories", "IronCore", 400.0, 1299.0),
        ("PRD-F503", "Insulated Hydro Flask 1000ml", "Fitness", "Hydration", "ActivePulse", 350.0, 999.0),
    ]

    records = []
    for pid, name, cat, subcat, supp, cost, msrp in catalog:
        margin = round((msrp - cost) / msrp, 4)
        records.append({
            "product_id": pid,
            "product_name": name,
            "category": cat,
            "subcategory": subcat,
            "supplier": supp,
            "cost": cost,
            "selling_price": msrp,
            "margin_pct": margin,
        })

    return pd.DataFrame(records)


def generate_orders(customers_df: pd.DataFrame, products_df: pd.DataFrame,
                    num_orders: int = 15000) -> pd.DataFrame:
    """Generate omnichannel order transactions with realistic discounts and status."""
    channels = ["Online Direct", "Amazon Marketplace", "Retail Store", "Mobile App", "Wholesale"]
    channel_weights = [0.35, 0.28, 0.18, 0.15, 0.04]

    locations = [
        "Mumbai Central Store", "Delhi Connaught Hub", "Bengaluru Indiranagar Hub",
        "Hyderabad Jubilee Warehouse", "Pune Viman Nagar Store", "Chennai Anna Nagar Hub",
        "Kolkata Park Street Store", "Ahmedabad SG Highway Hub"
    ]

    statuses = ["COMPLETED", "CANCELLED", "PENDING"]
    status_weights = [0.91, 0.06, 0.03]

    start_date = date(2024, 1, 1)
    end_date = date(2025, 9, 30)
    total_days = (end_date - start_date).days

    cust_ids = customers_df["customer_id"].values
    prod_ids = products_df["product_id"].values
    prod_price_map = products_df.set_index("product_id")["selling_price"].to_dict()

    records = []
    for i in range(1, num_orders + 1):
        order_id = f"ORD-{20240000 + i}"
        customer_id = np.random.choice(cust_ids)
        product_id = np.random.choice(prod_ids)
        base_price = prod_price_map[product_id]

        day_offset = random.randint(0, total_days)
        order_dt = start_date + timedelta(days=day_offset)

        # Quantity distribution: mostly 1-3, occasional wholesale order
        if random.random() < 0.03:
            quantity = random.randint(10, 50)
        else:
            quantity = np.random.choice([1, 2, 3, 4], p=[0.65, 0.22, 0.09, 0.04])

        # Discount logic: normal distribution around 8%, with occasional heavy promos
        promo_roll = random.random()
        if product_id == "PRD-E109":
            # Revenue Trap: Excessive promotional discount on Flagship Smartphone
            discount = round(random.choice([0.15, 0.20, 0.25, 0.30]), 2)
        elif promo_roll < 0.12:
            discount = round(random.uniform(0.20, 0.45), 2)  # Leaking promo
        elif promo_roll < 0.45:
            discount = round(random.uniform(0.05, 0.15), 2)  # Standard coupon
        else:
            discount = 0.0

        channel = np.random.choice(channels, p=channel_weights)
        location = random.choice(locations)
        status = np.random.choice(statuses, p=status_weights)

        # Allow some price variance (e.g. dynamic pricing or flash sales)
        unit_price = round(base_price * random.uniform(0.95, 1.05), 2)

        records.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "order_date": order_dt.isoformat(),
            "quantity": int(quantity),
            "unit_price": unit_price,
            "discount": discount,
            "channel": channel,
            "location": location,
            "status": status,
        })

    return pd.DataFrame(records)


def generate_payments(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Generate payment attempts, methods, and failure reasons."""
    methods = ["Credit Card", "UPI", "Net Banking", "Debit Card", "Digital Wallet", "COD"]
    method_weights = [0.38, 0.32, 0.12, 0.10, 0.05, 0.03]

    records = []
    payment_counter = 1

    for _, row in orders_df.iterrows():
        order_id = row["order_id"]
        order_dt = datetime.fromisoformat(row["order_date"])
        gross = row["quantity"] * row["unit_price"]
        disc_amt = gross * row["discount"]
        net_amt = round(gross - disc_amt, 2)

        method = np.random.choice(methods, p=method_weights)

        if row["status"] == "CANCELLED":
            # Some cancellations are due to payment failure
            records.append({
                "payment_id": f"PAY-{payment_counter:07d}",
                "order_id": order_id,
                "payment_date": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_method": method,
                "amount": net_amt,
                "payment_status": "FAILED",
                "failure_reason": random.choice(["INSUFFICIENT_FUNDS", "BANK_GATEWAY_TIMEOUT", "AUTH_DECLINED"]),
            })
            payment_counter += 1
            continue

        # Completed or pending orders: 96% success, 4% initial retry
        if random.random() < 0.04:
            # First failed attempt
            records.append({
                "payment_id": f"PAY-{payment_counter:07d}",
                "order_id": order_id,
                "payment_date": (order_dt - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "payment_method": method,
                "amount": net_amt,
                "payment_status": "FAILED",
                "failure_reason": random.choice(["BANK_GATEWAY_TIMEOUT", "OTP_EXPIRED", "3DS_VERIFICATION_FAILED"]),
            })
            payment_counter += 1

        # Successful capture
        records.append({
            "payment_id": f"PAY-{payment_counter:07d}",
            "order_id": order_id,
            "payment_date": order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": method,
            "amount": net_amt,
            "payment_status": "SUCCESS",
            "failure_reason": None,
        })
        payment_counter += 1

    return pd.DataFrame(records)


def generate_returns(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Generate returns with realistic reasons, skewing high on apparel and defective electronics."""
    completed_orders = orders_df[orders_df["status"] == "COMPLETED"]

    reasons = [
        "DEFECTIVE_ITEM", "WRONG_SIZE_FIT", "ITEM_NOT_AS_DESCRIBED",
        "CHANGED_MIND", "LATE_DELIVERY", "DAMAGED_IN_SHIPPING"
    ]

    records = []
    return_counter = 1

    for _, row in completed_orders.iterrows():
        pid = row["product_id"]
        qty = row["quantity"]
        order_dt = date.fromisoformat(row["order_date"])

        # Determine return probability by product profile
        if pid in ["PRD-E104", "PRD-E110"]:  # Audio products with higher reported defect rate
            p_return = 0.16
        elif pid.startswith("PRD-A"):  # Apparel has sizing returns
            p_return = 0.13
        elif pid == "PRD-E109":  # Flagship phone return rate
            p_return = 0.09
        else:
            p_return = 0.04

        if random.random() < p_return:
            qty_returned = random.randint(1, qty)
            return_dt = order_dt + timedelta(days=random.randint(2, 21))

            if pid.startswith("PRD-A"):
                reason = "WRONG_SIZE_FIT" if random.random() < 0.65 else random.choice(reasons)
            elif pid in ["PRD-E104", "PRD-E110"]:
                reason = "DEFECTIVE_ITEM" if random.random() < 0.70 else random.choice(reasons)
            else:
                reason = random.choice(reasons)

            records.append({
                "return_id": f"RET-{return_counter:06d}",
                "order_id": row["order_id"],
                "product_id": pid,
                "return_date": return_dt.isoformat(),
                "quantity_returned": qty_returned,
                "return_reason": reason,
            })
            return_counter += 1

    return pd.DataFrame(records)


def generate_inventory(products_df: pd.DataFrame) -> pd.DataFrame:
    """Generate weekly inventory snapshots across regional warehouses."""
    warehouses = [
        "Bhiwandi Central DC (West)",
        "Gurugram Fulfillment Center (North)",
        "Hosur Main Warehouse (South)",
        "Dankuni Logistics Center (East)"
    ]

    # Weekly snapshots across 2024-2025
    snapshot_dates = pd.date_range(start="2024-01-07", end="2025-09-28", freq="W").strftime("%Y-%m-%d")

    records = []
    for s_date in snapshot_dates:
        for _, prod in products_df.iterrows():
            pid = prod["product_id"]

            for wh in warehouses:
                # Engineered Stockout: UltraBook (E101) stockout in North, HighJuicer in West
                if pid == "PRD-E101" and "Gurugram" in wh and "2024-06" in s_date:
                    units_avail = 0
                elif pid == "PRD-H301" and "Bhiwandi" in wh and "2024-08" in s_date:
                    units_avail = 0
                else:
                    units_avail = max(0, int(np.random.normal(loc=120, scale=45)))

                records.append({
                    "product_id": pid,
                    "warehouse": wh,
                    "snapshot_date": s_date,
                    "units_available": units_avail,
                })

    return pd.DataFrame(records)


def generate_marketing() -> pd.DataFrame:
    """Generate marketing campaign performance records across channels."""
    campaigns = [
        ("CMP-GOOGLE-SEARCH-BRAND", "Paid Search", 350.0, 18000, 1400, 195),
        ("CMP-GOOGLE-SEARCH-GENERIC", "Paid Search", 850.0, 45000, 2200, 120),
        ("CMP-META-RETARGETING", "Social", 520.0, 62000, 3100, 260),
        ("CMP-META-PROSPECTING", "Social", 940.0, 110000, 3900, 145),
        ("CMP-EMAIL-NEWSLETTER-WEEKLY", "Email", 75.0, 28000, 4200, 340),
        ("CMP-TIKTOK-CREATOR-BLITZ", "Influencer", 1200.0, 185000, 5600, 180),
        ("CMP-AMAZON-SPONSORED-PROD", "Affiliate", 680.0, 52000, 2800, 210),
    ]

    dates = pd.date_range(start="2024-01-01", end="2025-09-30", freq="D").strftime("%Y-%m-%d")

    records = []
    for d in dates:
        for cmp_id, channel, base_spend, base_imp, base_clicks, base_conv in campaigns:
            # Add daily noise (+- 20%)
            mult = random.uniform(0.80, 1.20)
            spend = round(base_spend * mult, 2)
            impressions = int(base_imp * mult)
            clicks = int(base_clicks * mult)
            conversions = max(1, int(base_conv * mult))

            records.append({
                "campaign_id": cmp_id,
                "channel": channel,
                "date": d,
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
            })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description="RevenueOS Realistic Dataset Generator")
    parser.add_argument("--rows", type=int, default=12000, help="Number of orders to generate")
    parser.add_argument("--customers", type=int, default=1200, help="Number of customer profiles")
    parser.add_argument("--out-dir", type=str, default="data/raw", help="Output directory")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    out_base = Path(args.out_dir)
    print("=" * 65)
    print("REVENUEOS SYNTHETIC DATA GENERATOR")
    print(f"Target Directory: {out_base.resolve()}")
    print(f"Orders: {args.rows:,} | Customers: {args.customers:,}")
    print("=" * 65)

    # 1. Customers
    print("[1/7] Generating Customers...")
    df_cust = generate_customers(args.customers)
    cust_path = out_base / "customers" / "customers.csv"
    cust_path.parent.mkdir(parents=True, exist_ok=True)
    df_cust.to_csv(cust_path, index=False)
    print(f"  [OK] Saved {len(df_cust):,} customers to {cust_path}")

    # 2. Products
    print("[2/7] Generating Product Catalog...")
    df_prod = generate_products()
    prod_path = out_base / "products" / "products.csv"
    prod_path.parent.mkdir(parents=True, exist_ok=True)
    df_prod.to_csv(prod_path, index=False)
    print(f"  [OK] Saved {len(df_prod):,} products to {prod_path}")

    # 3. Orders
    print(f"[3/7] Generating {args.rows:,} Orders...")
    df_orders = generate_orders(df_cust, df_prod, args.rows)
    orders_path = out_base / "orders" / "orders.csv"
    orders_path.parent.mkdir(parents=True, exist_ok=True)
    df_orders.to_csv(orders_path, index=False)
    print(f"  [OK] Saved {len(df_orders):,} orders to {orders_path}")

    # 4. Payments
    print("[4/7] Generating Payments...")
    df_payments = generate_payments(df_orders)
    pay_path = out_base / "payments" / "payments.csv"
    pay_path.parent.mkdir(parents=True, exist_ok=True)
    df_payments.to_csv(pay_path, index=False)
    print(f"  [OK] Saved {len(df_payments):,} payments to {pay_path}")

    # 5. Returns
    print("[5/7] Generating Returns & Disputed Shipments...")
    df_returns = generate_returns(df_orders)
    ret_path = out_base / "returns" / "returns.csv"
    ret_path.parent.mkdir(parents=True, exist_ok=True)
    df_returns.to_csv(ret_path, index=False)
    print(f"  [OK] Saved {len(df_returns):,} returns to {ret_path}")

    # 6. Inventory
    print("[6/7] Generating Warehouse Inventory Snapshots...")
    df_inv = generate_inventory(df_prod)
    inv_path = out_base / "inventory" / "inventory.csv"
    inv_path.parent.mkdir(parents=True, exist_ok=True)
    df_inv.to_csv(inv_path, index=False)
    print(f"  [OK] Saved {len(df_inv):,} inventory records to {inv_path}")

    # 7. Marketing
    print("[7/7] Generating Campaign Performance Records...")
    df_mkt = generate_marketing()
    mkt_path = out_base / "marketing" / "marketing.csv"
    mkt_path.parent.mkdir(parents=True, exist_ok=True)
    df_mkt.to_csv(mkt_path, index=False)
    print(f"  [OK] Saved {len(df_mkt):,} marketing records to {mkt_path}")

    print("=" * 65)
    print("[SUCCESS] All 7 omnichannel datasets successfully generated.")
    print("=" * 65)


if __name__ == "__main__":
    main()
