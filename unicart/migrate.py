"""Idempotent, non-destructive upgrade of an existing UniCart database.  Run:  python -m unicart.migrate

Changes relative to the report's schema.sql (see docs/DATABASE_DESIGN.md):
  1. support_request.response            - staff reply to a customer request (UC-23)
  2. interaction_log.event_type allows REC_IMPRESSION - required to compute CTR (formula 3.3)
  3. product_embedding table - vectors for AI semantic search (ProductEmbedding, section 3.6.2)
  4. book / electronics / fashion / furniture - Product specialisation (class-table inheritance); each new table is
     filled from the existing product rows of the matching categories (product.attributes and product.brand are kept)
"""
from sqlalchemy import text

from .persistence.database import Database

_EMBEDDING_TABLE = """
CREATE TABLE product_embedding (
    product_id    BIGINT PRIMARY KEY,
    model         VARCHAR(60) NOT NULL,
    dim           INT NOT NULL,
    content_hash  CHAR(32) NOT NULL,
    vector        BLOB NOT NULL,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_product FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
) ENGINE=InnoDB
"""
_EVENTS = "'VIEW','SEARCH','ADD_TO_CART','PURCHASE','CLICK_REC','REC_IMPRESSION'"

_WARRANTY = "JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.warranty'))"
# subtype table -> (column definitions, categories it specialises, SELECT list used to fill it from product p)
_SUBTYPES = {
    "book": (
        "isbn VARCHAR(255), author VARCHAR(255), publisher VARCHAR(255), page_count INT, language VARCHAR(255)",
        ("Books",),
        "(product_id, isbn, author, publisher) SELECT p.id, JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.isbn')), "
        "JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.author')), p.brand"),
    "electronics": (
        "brand VARCHAR(255), model_number VARCHAR(255), warranty_months INT",
        ("Electronics",),
        "(product_id, brand, warranty_months) SELECT p.id, p.brand, COALESCE("
        "CAST(JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.warrantyMonths')) AS UNSIGNED), CASE "
        f"WHEN {_WARRANTY} REGEXP '^[0-9]+ tháng$' THEN CAST(SUBSTRING_INDEX({_WARRANTY}, ' ', 1) AS UNSIGNED) "
        f"WHEN {_WARRANTY} REGEXP '^[0-9]+ năm$' THEN 12 * CAST(SUBSTRING_INDEX({_WARRANTY}, ' ', 1) AS UNSIGNED) "
        f"WHEN {_WARRANTY} = 'Không bảo hành' THEN 0 END)"),
    "fashion": (
        "size VARCHAR(255), color VARCHAR(255), material VARCHAR(255)",
        ("Clothes", "Shoes"),
        "(product_id, size, color, material) SELECT p.id, COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.size')), "
        "JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.shoesSize'))), JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.color')), "
        "JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.material'))"),
    "furniture": (
        "material VARCHAR(255), width_cm INT, depth_cm INT, height_cm INT, weight_kg INT, assembly_required BOOLEAN",
        ("Nội thất & trang trí",),
        "(product_id, material) SELECT p.id, JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.material'))"),
}


def migrate(db: Database | None = None) -> list[str]:
    db = db or Database()
    done: list[str] = []
    with db.engine.begin() as c:
        has_response = c.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() "
            "AND table_name = 'support_request' AND column_name = 'response'")).scalar()
        if not has_response:
            c.execute(text("ALTER TABLE support_request ADD COLUMN response TEXT NULL AFTER handled_by"))
            done.append("support_request.response")
        clause = c.execute(text(
            "SELECT check_clause FROM information_schema.check_constraints "
            "WHERE constraint_schema = DATABASE() AND constraint_name = 'ck_log_event'")).scalar()
        if clause is not None and "REC_IMPRESSION" not in clause:
            c.execute(text("ALTER TABLE interaction_log DROP CHECK ck_log_event"))
            c.execute(text(f"ALTER TABLE interaction_log ADD CONSTRAINT ck_log_event CHECK (event_type IN ({_EVENTS}))"))
            done.append("interaction_log.ck_log_event")
        has_table = c.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() "
            "AND table_name = 'product_embedding'")).scalar()
        if not has_table:
            c.execute(text(_EMBEDDING_TABLE))
            done.append("product_embedding")
        for table, (columns, categories, fill) in _SUBTYPES.items():
            exists = c.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() "
                "AND table_name = :t"), {"t": table}).scalar()
            if exists:
                continue
            c.exec_driver_sql(
                f"CREATE TABLE {table} (product_id BIGINT PRIMARY KEY, {columns}, CONSTRAINT fk_{table}_product "
                "FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE) ENGINE=InnoDB")
            names = ", ".join("'" + n + "'" for n in categories)
            c.exec_driver_sql(f"INSERT INTO {table} {fill} FROM product p JOIN category c ON c.id = p.category_id "
                              f"WHERE c.name IN ({names})")
            done.append(table)
    return done


if __name__ == "__main__":
    applied = migrate()
    print("applied: " + ", ".join(applied) if applied else "database is already up to date")
