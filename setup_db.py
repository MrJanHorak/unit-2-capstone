# setup_db.py
import sqlite3
import os

os.makedirs("./data", exist_ok=True)
db_path = "./data/database.sqlite"

# Remove existing database to ensure a clean setup
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Sales Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    region TEXT,
    product TEXT,
    revenue REAL,
    date TEXT,
    units_sold INTEGER
)
""")

# 2. Customers Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    industry TEXT,
    churn_date TEXT,
    satisfaction_score REAL
)
""")

# 3. Employees Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    department TEXT,
    satisfaction_score REAL,
    tenure_years INTEGER
)
""")

# Seed Sales Data across multiple quarters and regions
sales_data = [
    # Q4 2025
    ("North America", "Enterprise Tier", 120000.0, "2025-10-12", 12),
    ("EMEA", "Professional Tier", 45000.0, "2025-11-05", 30),
    ("APAC", "Starter Tier", 12000.0, "2025-11-20", 40),
    ("North America", "Professional Tier", 60000.0, "2025-12-01", 40),
    ("LATAM", "Starter Tier", 8000.0, "2025-12-15", 25),
    # Q1 2026
    ("North America", "Enterprise Tier", 150000.0, "2026-01-10", 15),
    ("EMEA", "Enterprise Tier", 110000.0, "2026-01-18", 11),
    ("APAC", "Professional Tier", 50000.0, "2026-02-02", 32),
    ("LATAM", "Professional Tier", 35000.0, "2026-02-14", 22),
    ("North America", "Starter Tier", 18000.0, "2026-03-01", 60),
    ("EMEA", "Professional Tier", 48000.0, "2026-03-22", 31),
    # Q2 2026
    ("North America", "Enterprise Tier", 180000.0, "2026-04-05", 18),
    ("APAC", "Enterprise Tier", 95000.0, "2026-04-19", 9),
    ("EMEA", "Starter Tier", 15000.0, "2026-05-11", 50),
    ("LATAM", "Starter Tier", 10000.0, "2026-06-01", 30),
]
cursor.executemany("INSERT INTO sales (region, product, revenue, date, units_sold) VALUES (?, ?, ?, ?, ?)", sales_data)

# Seed Customers Data with mix of Active/Churned and varying scores
customers_data = [
    ("Acme Corp", "Fintech", None, 4.8),
    ("Beta LLC", "Healthcare", "2025-11-10", 2.3),
    ("Gamma Inc", "Retail", None, 4.2),
    ("Delta Systems", "Fintech", None, 4.9),
    ("Epsilon Logistics", "Transportation", "2026-01-15", 1.8),
    ("Zeta Health", "Healthcare", None, 3.9),
    ("Eta Global", "Retail", None, 4.5),
    ("Theta Media", "Entertainment", "2026-02-28", 2.1),
    ("Iota Solutions", "Fintech", None, 4.7),
    ("Kappa Tech", "Software", None, 4.1),
    ("Lambda Cloud", "Software", None, 4.6),
    ("Mu Dynamics", "Transportation", "2026-03-04", 2.5),
]
cursor.executemany("INSERT INTO customers (name, industry, churn_date, satisfaction_score) VALUES (?, ?, ?, ?)", customers_data)

# Seed Employees Data across departments, tenure, and satisfaction scores
employees_data = [
    ("Engineering", 4.5, 3),
    ("Engineering", 4.8, 6),
    ("Engineering", 4.1, 1),
    ("Engineering", 3.9, 2),
    ("Customer Experience", 3.8, 2),
    ("Customer Experience", 3.2, 1),
    ("Customer Experience", 4.0, 4),
    ("Sales", 4.1, 5),
    ("Sales", 3.5, 2),
    ("Sales", 4.6, 7),
    ("Security", 4.7, 4),
    ("Security", 4.4, 3),
    ("Product", 3.9, 3),
    ("Product", 4.2, 5),
]
cursor.executemany("INSERT INTO employees (department, satisfaction_score, tenure_years) VALUES (?, ?, ?)", employees_data)

conn.commit()
conn.close()
print("Database updated with expanded test dataset at ./data/database.sqlite")