#!/usr/bin/env python3
"""
Database Initialization & Verification Script
Checks connection to MySQL and verifies database tables in ecommerce.
"""

import os
import sys
from data.db_config import get_db_config
from data.db_connection import get_connection, test_connection, get_driver_name


def run_init_db():
    print("=" * 65)
    print("  MySQL Database Verification & Connection Tool")
    print("  Multimodal Search System (Assignment 05 & 06)")
    print("=" * 65)

    driver = get_driver_name()
    print(f"[*] Detected MySQL Driver: {driver}")
    if not driver:
        print("[!] Error: No MySQL driver installed. Please run:")
        print("    pip install mysql-connector-python pymysql")
        return

    cfg = get_db_config()
    print(f"[*] Target Host: {cfg['host']}:{cfg['port']}")
    print(f"[*] Target User: {cfg['user']}")
    print(f"[*] Target Database: {cfg['database']}")
    print(f"[*] Password configured: {'Yes (Length ' + str(len(cfg['password'])) + ')' if cfg['password'] else 'No (Empty)'}")
    print("-" * 65)

    # 1. Test basic connection
    ok, msg, details = test_connection()
    if not ok:
        print(f"[!] Warning: Cannot connect to target database '{cfg['database']}':")
        print(f"    {msg}")
        return

    print(f"[+] {msg}")

    # 2. Inspect existing tables in the database
    conn = get_connection(use_database=True)
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES;")
    raw_tables = cursor.fetchall()
    table_names = []
    for t in raw_tables:
        tname = list(t.values())[0] if isinstance(t, dict) else t[0]
        table_names.append(tname)

    print(f"[*] Tables found in '{cfg['database']}': {', '.join(table_names) if table_names else '(Empty)'}")

    # Check for Product / products
    lower_tables = {t.lower(): t for t in table_names}
    if "product" in lower_tables:
        actual_name = lower_tables["product"]
        cursor.execute(f"SELECT COUNT(*) FROM `{actual_name}`;")
        cnt = cursor.fetchone()
        count = list(cnt.values())[0] if isinstance(cnt, dict) else cnt[0]
        print(f"[+] Found product table: `{actual_name}` with {count} products.")

    if "order" in lower_tables:
        actual_name = lower_tables["order"]
        cursor.execute(f"SELECT COUNT(*) FROM `{actual_name}`;")
        cnt = cursor.fetchone()
        count = list(cnt.values())[0] if isinstance(cnt, dict) else cnt[0]
        print(f"[+] Found order table: `{actual_name}` with {count} orders.")

    if "orderitem" in lower_tables or "order_items" in lower_tables:
        actual_name = lower_tables.get("orderitem") or lower_tables.get("order_items")
        cursor.execute(f"SELECT COUNT(*) FROM `{actual_name}`;")
        cnt = cursor.fetchone()
        count = list(cnt.values())[0] if isinstance(cnt, dict) else cnt[0]
        print(f"[+] Found order items table: `{actual_name}` with {count} items.")

    cursor.close()
    conn.close()

    print("-" * 65)
    print("[SUCCESS] MySQL is fully connected and ready for the application!")
    print("          You can now run: python3 main.py")


if __name__ == "__main__":
    run_init_db()
