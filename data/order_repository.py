from typing import List, Dict, Any, Optional
from .db_connection import get_connection, test_connection


class OrderRepository:
    """
    Data Layer: Order Repository
    Responsible for storing and retrieving customer order information.
    Supports:
      1. User's existing MySQL 'ecommerce' database (`Order`, `OrderItem`)
      2. MySQL 'orders' schema from schema.sql
      3. Automatic in-memory fallback
    """

    def __init__(self, use_db: bool = True):
        self.orders: List[Dict[str, Any]] = []
        self.data_source: str = "memory"
        self.use_db = use_db

        # 1. Attempt loading from MySQL if enabled
        if self.use_db:
            loaded_from_mysql = self._load_from_mysql()
            if loaded_from_mysql:
                print(f"[OrderRepository] [OK] Loaded {len(self.orders)} orders from MySQL ({self.data_source}).")
                return

        # 2. Fallback to in-memory orders
        self.data_source = "memory_fallback"
        self._load_fallback_memory()
        print(f"[OrderRepository] [Notice] Loaded {len(self.orders)} orders from memory fallback.")

    def _load_from_mysql(self) -> bool:
        """Loads orders and order items from MySQL database."""
        try:
            conn = get_connection(use_database=True)
            cursor = conn.cursor()

            cursor.execute("SHOW TABLES;")
            raw_tables = cursor.fetchall()
            existing_tables = set()
            for t in raw_tables:
                name = list(t.values())[0] if isinstance(t, dict) else t[0]
                existing_tables.add(name.lower())

            # Case A: User's ecommerce database (`Order`, `OrderItem`)
            if "order" in existing_tables:
                cursor.execute("SELECT orderID, cusID, orderDate, totalAmount, status FROM `Order` ORDER BY orderDate DESC;")
                orders_rows = cursor.fetchall()

                # Query OrderItem
                items_by_order: Dict[str, List[Dict[str, Any]]] = {}
                if "orderitem" in existing_tables:
                    cursor.execute("""
                        SELECT i.orderID, i.productID, i.quantity, i.unitPrice, p.name AS product_name
                        FROM OrderItem i
                        LEFT JOIN Product p ON i.productID = p.productID;
                    """)
                    items_rows = cursor.fetchall()
                    for it in items_rows:
                        if isinstance(it, dict):
                            oid = str(it["orderID"])
                            pid = str(it["productID"])
                            qty = int(it.get("quantity") or 1)
                            price = float(it.get("unitPrice") or 0.0)
                            pname = str(it.get("product_name") or f"Product #{pid}")
                        else:
                            oid = str(it[0])
                            pid = str(it[1])
                            qty = int(it[2] or 1)
                            price = float(it[3] or 0.0)
                            pname = str(it[4] or f"Product #{pid}")

                        if oid not in items_by_order:
                            items_by_order[oid] = []
                        items_by_order[oid].append({
                            "product_id": pid,
                            "product_name": pname,
                            "quantity": qty,
                            "price": price
                        })

                parsed = []
                for o in orders_rows:
                    if isinstance(o, dict):
                        oid = str(o["orderID"])
                        cid = str(o["cusID"])
                        dt = str(o["orderDate"])
                        tot = float(o.get("totalAmount") or 0.0)
                        st = str(o.get("status") or "Processing")
                    else:
                        oid = str(o[0])
                        cid = str(o[1])
                        dt = str(o[2])
                        tot = float(o[3] or 0.0)
                        st = str(o[4] or "Processing")

                    parsed.append({
                        "order_id": oid,
                        "orderID": oid,
                        "customer_id": cid,
                        "date": dt,
                        "status": st,
                        "total": tot,
                        "items": items_by_order.get(oid, [])
                    })

                cursor.close()
                conn.close()

                if parsed:
                    self.orders = parsed
                    self.data_source = "mysql (`Order` table)"
                    return True

            # Case B: Standard 'orders' table
            elif "orders" in existing_tables:
                cursor.execute("SELECT order_id, customer_id, order_date, status, total FROM orders ORDER BY order_date DESC;")
                orders_rows = cursor.fetchall()

                cursor.execute("SELECT order_id, product_id, quantity, price FROM order_items;")
                items_rows = cursor.fetchall()
                items_by_order = {}
                for item in items_rows:
                    if isinstance(item, dict):
                        oid = str(item["order_id"])
                        pid = item["product_id"]
                        qty = int(item["quantity"])
                        price = float(item["price"])
                    else:
                        oid = str(item[0])
                        pid = item[1]
                        qty = int(item[2])
                        price = float(item[3])

                    if oid not in items_by_order:
                        items_by_order[oid] = []
                    items_by_order[oid].append({
                        "product_id": pid,
                        "quantity": qty,
                        "price": price
                    })

                parsed = []
                for o in orders_rows:
                    if isinstance(o, dict):
                        oid = str(o["order_id"])
                        cid = str(o["customer_id"])
                        dt = str(o["order_date"])
                        st = str(o["status"])
                        tot = float(o["total"])
                    else:
                        oid = str(o[0])
                        cid = str(o[1])
                        dt = str(o[2])
                        st = str(o[3])
                        tot = float(o[4])

                    parsed.append({
                        "order_id": oid,
                        "orderID": oid,
                        "customer_id": cid,
                        "date": dt,
                        "status": st,
                        "total": tot,
                        "items": items_by_order.get(oid, [])
                    })

                cursor.close()
                conn.close()

                if parsed:
                    self.orders = parsed
                    self.data_source = "mysql (orders table)"
                    return True

            cursor.close()
            conn.close()
            return False

        except Exception as e:
            print(f"[OrderRepository] MySQL error: {e}")
            return False

    def _load_fallback_memory(self):
        """Embedded fallback order data."""
        self.orders = [
            {
                "order_id": "O001",
                "customer_id": "C001",
                "date": "2026-09-25",
                "status": "Shipped",
                "total": 150.0,
                "items": [{"product_id": "PROD001", "quantity": 1, "price": 120.0}]
            },
            {
                "order_id": "O002",
                "customer_id": "C002",
                "date": "2026-09-28",
                "status": "Delivered",
                "total": 80.0,
                "items": [{"product_id": "PROD003", "quantity": 1, "price": 80.0}]
            }
        ]

    def all_orders(self) -> List[Dict[str, Any]]:
        """Returns all orders."""
        return self.orders

    def find_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Find an order by its order ID (case-insensitive)."""
        normalized_id = str(order_id).strip().upper()
        for order in self.orders:
            if order.get("order_id", "").strip().upper() == normalized_id:
                return order
            if order.get("orderID", "").strip().upper() == normalized_id:
                return order
        return None

    def find_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Find orders belonging to a specific customer."""
        normalized_cust = str(customer_id).strip().upper()
        return [
            order for order in self.orders
            if order.get("customer_id", "").strip().upper() == normalized_cust
            or order.get("cusID", "").strip().upper() == normalized_cust
        ]

    def refresh(self) -> bool:
        """Reloads orders from MySQL if connected."""
        if self.use_db and self._load_from_mysql():
            return True
        return False
