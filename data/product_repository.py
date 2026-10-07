import json
import os
from typing import List, Dict, Any, Optional
from .db_connection import get_connection, test_connection


# Category prototype embeddings for 3D multimodal search
CATEGORY_EMBEDDINGS = {
    "shoes": [0.9, 0.1, 0.2],
    "bag": [0.1, 0.2, 0.9],
    "clothes": [0.3, 0.7, 0.4],
    "clothing": [0.3, 0.7, 0.4],
    "laptop": [0.2, 0.8, 0.1],
    "mobile": [0.4, 0.5, 0.6],
    "book": [0.1, 0.3, 0.85],
    "electronic": [0.2, 0.4, 0.9],
    "accessories": [0.4, 0.5, 0.6]
}

CATEGORY_IMAGES = {
    "shoes": "images/blue_sports_shoes.png",
    "bag": "images/black_leather_bag.png",
    "clothes": "images/white_casual_tshirt.png",
    "clothing": "images/white_casual_tshirt.png",
    "laptop": "images/smart_fitness_watch.png",
    "mobile": "images/smart_fitness_watch.png",
    "book": "images/black_leather_bag.png",
    "electronic": "images/smart_fitness_watch.png",
    "accessories": "images/smart_fitness_watch.png"
}


class ProductRepository:
    """
    Data Layer: Product Repository
    Responsible for storing and retrieving product information.
    Supports:
      1. User's existing MySQL 'ecommerce' database (Product, Shoes, Clothes, Book, etc.)
      2. MySQL 'products' schema from schema.sql
      3. Automatic JSON fallback (products.json) if MySQL is offline.
    """

    def __init__(self, json_file_path: Optional[str] = None, use_db: bool = True):
        self.products: List[Dict[str, Any]] = []
        self.data_source: str = "json"
        self.use_db = use_db
        self.db_status_message: str = ""

        # 1. Attempt loading from MySQL if enabled
        if self.use_db:
            loaded_from_mysql = self._load_from_mysql()
            if loaded_from_mysql:
                print(f"[ProductRepository] [OK] Loaded {len(self.products)} products from MySQL ({self.data_source}).")
                return

        # 2. Fallback to products.json
        self.data_source = "json_fallback"
        if json_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_json = os.path.join(base_dir, "products.json")
            if os.path.exists(default_json):
                json_file_path = default_json

        if json_file_path and os.path.exists(json_file_path):
            with open(json_file_path, "r", encoding="utf-8") as f:
                self.products = json.load(f)
            print(f"[ProductRepository] [Notice] Loaded {len(self.products)} products from JSON fallback ({json_file_path}).")
        else:
            self._load_fallback_memory()
            print(f"[ProductRepository] [Notice] Loaded {len(self.products)} embedded products from memory.")

    def _load_from_mysql(self) -> bool:
        """Loads products from MySQL database (detects table structure)."""
        try:
            conn = get_connection(use_database=True)
            cursor = conn.cursor()

            # Check what tables exist
            cursor.execute("SHOW TABLES;")
            raw_tables = cursor.fetchall()
            existing_tables = set()
            for t in raw_tables:
                name = list(t.values())[0] if isinstance(t, dict) else t[0]
                existing_tables.add(name.lower())

            # Case A: Table 'Product' (from user's ecommerce database)
            if "product" in existing_tables:
                sql = """
                    SELECT 
                        p.productID,
                        p.name,
                        p.description,
                        p.price,
                        p.stockQuantity,
                        p.productType,
                        c.color AS clothes_color,
                        s.shoesType AS shoes_type
                    FROM Product p
                    LEFT JOIN Clothes c ON p.productID = c.productID
                    LEFT JOIN Shoes s ON p.productID = s.productID
                    ORDER BY p.productID ASC;
                """
                cursor.execute(sql)
                rows = cursor.fetchall()
                products_list = []
                for r in rows:
                    if isinstance(r, dict):
                        pid = str(r["productID"])
                        name = str(r["name"])
                        desc = str(r.get("description") or "")
                        price = float(r.get("price") or 0.0)
                        stock = int(r.get("stockQuantity") or 0)
                        ptype = str(r.get("productType") or "General").lower()
                        color = str(r.get("clothes_color") or "")
                        stype = str(r.get("shoes_type") or "")
                    else:
                        pid = str(r[0])
                        name = str(r[1])
                        desc = str(r[2] or "")
                        price = float(r[3] or 0.0)
                        stock = int(r[4] or 0)
                        ptype = str(r[5] or "General").lower()
                        color = str(r[6] or "")
                        stype = str(r[7] or "")

                    if not color:
                        if "trắng" in name.lower() or "white" in name.lower():
                            color = "white"
                        elif "đen" in name.lower() or "black" in name.lower():
                            color = "black"
                        elif "xanh" in name.lower() or "blue" in name.lower():
                            color = "blue"
                        elif ptype == "shoes":
                            color = "blue"
                        else:
                            color = "standard"

                    category = ptype
                    embedding = CATEGORY_EMBEDDINGS.get(category, [0.5, 0.5, 0.5])
                    img = CATEGORY_IMAGES.get(category, "images/nike_running_black.png")

                    products_list.append({
                        "id": pid,
                        "productID": pid,
                        "name": name,
                        "category": category,
                        "color": color,
                        "price": price,
                        "stock": stock,
                        "description": desc,
                        "image": img,
                        "embedding": embedding
                    })

                cursor.close()
                conn.close()

                if products_list:
                    self.products = products_list
                    self.data_source = "mysql (Product table)"
                    self.db_status_message = f"Connected to MySQL table 'Product'. Retrieved {len(products_list)} items."
                    return True

            # Case B: Table 'products' (from schema.sql)
            elif "products" in existing_tables:
                sql = """
                    SELECT id, name, category, color, price, stock, description, image, embedding
                    FROM products
                    ORDER BY id ASC;
                """
                cursor.execute(sql)
                rows = cursor.fetchall()
                products_list = []
                for r in rows:
                    if isinstance(r, dict):
                        pid = r["id"]
                        name = str(r["name"])
                        category = str(r.get("category", ""))
                        color = str(r.get("color", ""))
                        price = float(r.get("price", 0.0))
                        stock = int(r.get("stock", 0))
                        desc = str(r.get("description", ""))
                        image = str(r.get("image", ""))
                        raw_emb = r.get("embedding")
                    else:
                        pid = r[0]
                        name = str(r[1])
                        category = str(r[2])
                        color = str(r[3])
                        price = float(r[4])
                        stock = int(r[5])
                        desc = str(r[6])
                        image = str(r[7])
                        raw_emb = r[8]

                    embedding = [0.0, 0.0, 0.0]
                    if isinstance(raw_emb, list):
                        embedding = [float(x) for x in raw_emb]
                    elif isinstance(raw_emb, str):
                        try:
                            embedding = [float(x) for x in json.loads(raw_emb)]
                        except Exception:
                            embedding = [0.0, 0.0, 0.0]

                    products_list.append({
                        "id": pid,
                        "productID": str(pid),
                        "name": name,
                        "category": category,
                        "color": color,
                        "price": price,
                        "stock": stock,
                        "description": desc,
                        "image": image,
                        "embedding": embedding
                    })

                cursor.close()
                conn.close()

                if products_list:
                    self.products = products_list
                    self.data_source = "mysql (products table)"
                    self.db_status_message = f"Connected to MySQL table 'products'. Retrieved {len(products_list)} items."
                    return True

            cursor.close()
            conn.close()
            return False

        except Exception as e:
            self.db_status_message = f"MySQL connection skipped: {str(e)}"
            return False

    def _load_fallback_memory(self):
        """Embedded fallback if JSON file is missing."""
        self.products = [
            {"id": 1, "productID": "1", "name": "Nike Running Shoes", "category": "shoes", "color": "black", "price": 120.0, "stock": 10, "description": "High performance black running shoes with responsive cushioning.", "image": "images/nike_running_black.png", "embedding": [0.9, 0.1, 0.2]},
            {"id": 2, "productID": "2", "name": "Adidas Running Shoes", "category": "shoes", "color": "white", "price": 100.0, "stock": 15, "description": "Lightweight white running shoes designed for marathon endurance.", "image": "images/adidas_running_white.png", "embedding": [0.2, 0.8, 0.1]},
            {"id": 3, "productID": "3", "name": "Black Leather Bag", "category": "bag", "color": "black", "price": 80.0, "stock": 20, "description": "Premium black leather bag suitable for work and casual travel.", "image": "images/black_leather_bag.png", "embedding": [0.1, 0.2, 0.9]}
        ]

    def all_products(self) -> List[Dict[str, Any]]:
        """Returns all products in repository."""
        return self.products

    def find_by_id(self, product_id: Any) -> Optional[Dict[str, Any]]:
        """Find a product by its ID (supports both integer and string IDs)."""
        target = str(product_id).strip().lower()
        for product in self.products:
            if str(product.get("id", "")).strip().lower() == target:
                return product
            if str(product.get("productID", "")).strip().lower() == target:
                return product
        return None

    def refresh(self) -> bool:
        """Reloads products from MySQL if connected."""
        if self.use_db and self._load_from_mysql():
            return True
        return False
