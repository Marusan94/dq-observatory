"""Demo chaos dataset: 5000 customer_sales rows with deliberate real-world errors."""
import random
import pandas as pd
from pathlib import Path

random.seed(42)
N = 5000
cities = ["Bogota", "Bogotá", "bogota", "BOGOTA", "Bogotá D.C.", "Bogota DC", "Medellin", "Medellín",
          "MEDELLIN", "Cali", "CALI", "Barranquilla", "Cartagena"]
countries = ["Colombia", "colombia", "COLOMBIA", "Co", "Unknown", "N/A"]
statuses = ["active", "Active", "ACTIVE", "inactive", "pending", "PENDING", "unknown"]
segments = ["Retail", "retail", "RETAIL", "Enterprise", "enterprise", "SMB", "smb "]
missing_tokens = ["N/A", "NA", "null", "unknown", "-", "?", ""]

first = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Sofia", "Diego", "Laura", " JUAN ", "maria", "CARLOS"]
last = ["Perez", "Garcia", "Lopez", "Martinez", "Sanchez", "Pérez", "GARCIA", "lopez"]
products = ["Laptop", "laptop", "LAPTOP", "Mouse", "Keyboard", "Monitor", "Chair", "Desk"]

rows = []
for i in range(N):
    fn = random.choice(first)
    ln = random.choice(last)
    name = f"{fn} {ln}"
    if random.random() < 0.03:
        name = f"  {name}  "
    email = f"{fn.strip().lower()}.{ln.strip().lower()}@example.com"
    r = random.random()
    if r < 0.04:
        email = random.choice(["not-an-email", "missing@", "user@@example.com", " user@EXAMPLE.COM ", "N/A", ""])
    elif r < 0.06:
        email = email.upper()
    phone_formats = [f"+57 300 {random.randint(100,999)} {random.randint(1000,9999)}",
                     f"300{random.randint(1000000,9999999)}",
                     f"+57300{random.randint(1000000,9999999)}",
                     f"300-123-45{random.randint(10,99)}", "N/A", ""]
    phone = random.choice(phone_formats)
    age = random.randint(18, 80)
    if random.random() < 0.02:
        age = random.choice([-5, 200, 999])
    qty = random.randint(1, 10)
    if random.random() < 0.02:
        qty = random.choice([-2, -1])
    price = round(random.uniform(10, 2000), 2)
    price_cell = price
    if random.random() < 0.08:
        price_cell = random.choice([f"${price:,.2f}", f"{price}", f"{str(price).replace('.', ',')}", "N/A"])
    revenue = round((qty if isinstance(qty, int) and qty > 0 else 1) * (price if isinstance(price, (int, float)) else 100), 2)
    if random.random() < 0.015:
        revenue = -revenue
    if random.random() < 0.01:
        revenue = revenue * 20  # outlier
    signup = random.choice(["2026-09-24", "24/09/2026", "09/24/2026", "September 24 2026", "2026/09/24",
                            "03/04/2026", "not-a-date", "N/A"])
    last_p = random.choice(["2026-01-15", "15/01/2026", "N/A", ""])
    rows.append({"customer_id": f"C{10000+i}", "customer_name": name, "email": email, "phone": phone,
                 "country": random.choice(countries), "city": random.choice(cities),
                 "signup_date": signup, "age": age, "segment": random.choice(segments),
                 "product": random.choice(products), "quantity": qty, "unit_price": price_cell,
                 "revenue": revenue, "status": random.choice(statuses),
                 "last_purchase": last_p, "rating": random.choice([1, 2, 3, 4, 5, "N/A", ""])})
df = pd.DataFrame(rows)
# exact duplicates ~200
dup = df.sample(200, random_state=1)
df = pd.concat([df, dup], ignore_index=True)
# duplicate customer_ids
df.loc[df.sample(30, random_state=2).index, "customer_id"] = "C10001"
# constant-ish column
df["source_system"] = "ERP"
# empty strings sprinkle
for c in ["email", "phone", "city"]:
    df.loc[df.sample(40, random_state=3).index, c] = random.choice(missing_tokens)
out = Path(__file__).resolve().parents[1] / "data" / "demo" / "customers_sales.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"wrote {out} rows={len(df)} cols={len(df.columns)}")
