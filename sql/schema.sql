-- =====================================================================
-- UniCart - Database schema (MySQL 8 / MariaDB 10.6+)
-- Chapter 4.2 - Data model.
-- Run:  mysql -u root -p < schema.sql
-- =====================================================================
DROP DATABASE IF EXISTS unicart;
CREATE DATABASE unicart CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE unicart;

-- ---------- Account & customer ----------
CREATE TABLE role (
    id    TINYINT PRIMARY KEY,
    name  VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE account (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role_id        TINYINT NOT NULL,
    status         VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_role FOREIGN KEY (role_id) REFERENCES role(id),
    CONSTRAINT ck_account_status CHECK (status IN ('ACTIVE','LOCKED'))
) ENGINE=InnoDB;

CREATE TABLE customer (
    id             BIGINT PRIMARY KEY,
    first_name     VARCHAR(50) NOT NULL,
    middle_name    VARCHAR(50),
    last_name      VARCHAR(50) NOT NULL,
    phone          VARCHAR(20),
    loyalty_tier   VARCHAR(10) NOT NULL DEFAULT 'NEW',
    loyalty_point  INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_customer_account FOREIGN KEY (id) REFERENCES account(id) ON DELETE CASCADE,
    CONSTRAINT ck_customer_tier  CHECK (loyalty_tier IN ('NEW','REGULAR','VIP')),
    CONSTRAINT ck_customer_point CHECK (loyalty_point >= 0)
) ENGINE=InnoDB;

CREATE TABLE address (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id  BIGINT NOT NULL,
    recipient    VARCHAR(100) NOT NULL,
    phone        VARCHAR(20)  NOT NULL,
    street       VARCHAR(150) NOT NULL,
    district     VARCHAR(80),
    city         VARCHAR(80)  NOT NULL,
    country      VARCHAR(60)  NOT NULL DEFAULT 'Viet Nam',
    post_code    VARCHAR(15),
    is_default   BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_address_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------- Catalogue & inventory ----------
CREATE TABLE category (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    description  VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE product (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_id  BIGINT NOT NULL,
    sku          VARCHAR(40)  NOT NULL UNIQUE,
    name         VARCHAR(200) NOT NULL,
    description  TEXT,
    brand        VARCHAR(80),
    price        DECIMAL(12,2) NOT NULL,
    image_url    VARCHAR(255),
    attributes   JSON,                                   -- replaces Book/Laptop/Shoes... subclasses
    status       VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',  -- BR-01
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category(id),
    CONSTRAINT ck_product_price  CHECK (price >= 0),
    CONSTRAINT ck_product_status CHECK (status IN ('ACTIVE','HIDDEN')),
    INDEX idx_product_category (category_id),
    INDEX idx_product_name (name)
) ENGINE=InnoDB;

CREATE TABLE inventory (
    product_id     BIGINT PRIMARY KEY,
    quantity       INT NOT NULL DEFAULT 0,               -- NFR-15: never negative
    min_threshold  INT NOT NULL DEFAULT 5,               -- BR-11
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    CONSTRAINT ck_inventory_qty CHECK (quantity >= 0),
    CONSTRAINT ck_inventory_min CHECK (min_threshold >= 0)
) ENGINE=InnoDB;

CREATE TABLE promotion (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    code             VARCHAR(30) NOT NULL UNIQUE,
    discount_type    VARCHAR(10) NOT NULL,
    discount_value   DECIMAL(12,2) NOT NULL,
    min_order_value  DECIMAL(12,2) NOT NULL DEFAULT 0,
    start_at         DATETIME NOT NULL,
    end_at           DATETIME NOT NULL,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_promo_type  CHECK (discount_type IN ('PERCENT','AMOUNT')),
    CONSTRAINT ck_promo_value CHECK (discount_value > 0),
    CONSTRAINT ck_promo_date  CHECK (end_at > start_at)
) ENGINE=InnoDB;

-- ---------- Cart ----------
CREATE TABLE cart (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id  BIGINT NOT NULL UNIQUE,                 -- BR-02: one cart per customer
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cart_customer FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE cart_item (
    cart_id     BIGINT NOT NULL,
    product_id  BIGINT NOT NULL,
    quantity    INT NOT NULL,
    PRIMARY KEY (cart_id, product_id),
    CONSTRAINT fk_cartitem_cart    FOREIGN KEY (cart_id)    REFERENCES cart(id) ON DELETE CASCADE,
    CONSTRAINT fk_cartitem_product FOREIGN KEY (product_id) REFERENCES product(id),
    CONSTRAINT ck_cartitem_qty CHECK (quantity > 0)
) ENGINE=InnoDB;

-- ---------- Order ----------
CREATE TABLE customer_order (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    promotion_id    BIGINT,
    ship_recipient  VARCHAR(100) NOT NULL,               -- address snapshot at order time (FR-08)
    ship_phone      VARCHAR(20)  NOT NULL,
    ship_address    VARCHAR(300) NOT NULL,
    subtotal        DECIMAL(12,2) NOT NULL,
    discount        DECIMAL(12,2) NOT NULL DEFAULT 0,
    shipping_fee    DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount    DECIMAL(12,2) NOT NULL,              -- BR-05
    payment_method  VARCHAR(10) NOT NULL,
    status          VARCHAR(20) NOT NULL,                -- BR-07
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_customer  FOREIGN KEY (customer_id)  REFERENCES customer(id),
    CONSTRAINT fk_order_promotion FOREIGN KEY (promotion_id) REFERENCES promotion(id),
    CONSTRAINT ck_order_money  CHECK (subtotal >= 0 AND discount >= 0 AND shipping_fee >= 0 AND total_amount >= 0),
    CONSTRAINT ck_order_method CHECK (payment_method IN ('COD','ONLINE')),
    CONSTRAINT ck_order_status CHECK (status IN
        ('PENDING_PAYMENT','PENDING','CONFIRMED','PACKED','SHIPPING','DELIVERED','CANCELLED')),
    INDEX idx_order_customer (customer_id),
    INDEX idx_order_status (status)
) ENGINE=InnoDB;

CREATE TABLE order_item (
    order_id    BIGINT NOT NULL,
    product_id  BIGINT NOT NULL,
    quantity    INT NOT NULL,
    unit_price  DECIMAL(12,2) NOT NULL,                  -- price frozen at order time (BR-05)
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT fk_orderitem_order   FOREIGN KEY (order_id)   REFERENCES customer_order(id) ON DELETE CASCADE,
    CONSTRAINT fk_orderitem_product FOREIGN KEY (product_id) REFERENCES product(id),
    CONSTRAINT ck_orderitem_qty   CHECK (quantity > 0),
    CONSTRAINT ck_orderitem_price CHECK (unit_price >= 0)
) ENGINE=InnoDB;

CREATE TABLE order_status_history (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id    BIGINT NOT NULL,
    from_status VARCHAR(20),
    to_status   VARCHAR(20) NOT NULL,
    changed_by  BIGINT,                                  -- NULL = system / payment callback
    changed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_history_order   FOREIGN KEY (order_id)   REFERENCES customer_order(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_account FOREIGN KEY (changed_by) REFERENCES account(id)
) ENGINE=InnoDB;

CREATE TABLE stock_movement (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id  BIGINT NOT NULL,
    type        VARCHAR(10) NOT NULL,
    quantity    INT NOT NULL,
    reason      VARCHAR(100),
    order_id    BIGINT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stockmv_product FOREIGN KEY (product_id) REFERENCES product(id),
    CONSTRAINT fk_stockmv_order   FOREIGN KEY (order_id)   REFERENCES customer_order(id),
    CONSTRAINT ck_stockmv_type CHECK (type IN ('IN','OUT','RETURN','ADJUST')),
    CONSTRAINT ck_stockmv_qty  CHECK (quantity > 0)
) ENGINE=InnoDB;

CREATE TABLE payment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id        BIGINT NOT NULL UNIQUE,
    method          VARCHAR(10) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    status          VARCHAR(10) NOT NULL DEFAULT 'PENDING',
    transaction_id  VARCHAR(60) UNIQUE,                  -- idempotency for duplicate callbacks (UC-07 A3)
    paid_at         DATETIME,
    CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES customer_order(id) ON DELETE CASCADE,
    CONSTRAINT ck_payment_method CHECK (method IN ('COD','WALLET','CARD')),
    CONSTRAINT ck_payment_status CHECK (status IN ('PENDING','SUCCESS','FAILED')),
    CONSTRAINT ck_payment_amount CHECK (amount >= 0)
) ENGINE=InnoDB;

CREATE TABLE shipment (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id         BIGINT NOT NULL UNIQUE,
    carrier          VARCHAR(60),
    tracking_number  VARCHAR(60),
    status           VARCHAR(15) NOT NULL DEFAULT 'CREATED',
    delivery_date    DATE,
    CONSTRAINT fk_shipment_order FOREIGN KEY (order_id) REFERENCES customer_order(id) ON DELETE CASCADE,
    CONSTRAINT ck_shipment_status CHECK (status IN ('CREATED','IN_TRANSIT','DELIVERED','FAILED'))
) ENGINE=InnoDB;

-- ---------- Review, support, restock ----------
CREATE TABLE review (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id  BIGINT NOT NULL,
    product_id   BIGINT NOT NULL,
    order_id     BIGINT NOT NULL,
    rating       TINYINT NOT NULL,                       -- BR-09
    comment      TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (order_id, product_id),
    CONSTRAINT fk_review_customer FOREIGN KEY (customer_id) REFERENCES customer(id),
    CONSTRAINT fk_review_product  FOREIGN KEY (product_id)  REFERENCES product(id),
    CONSTRAINT fk_review_order    FOREIGN KEY (order_id)    REFERENCES customer_order(id),
    CONSTRAINT ck_review_rating CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE support_request (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id  BIGINT NOT NULL,
    order_id     BIGINT,
    content      TEXT NOT NULL,
    status       VARCHAR(12) NOT NULL DEFAULT 'OPEN',
    handled_by   BIGINT,
    response     TEXT,                                   -- staff reply (UC-23)
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_support_customer FOREIGN KEY (customer_id) REFERENCES customer(id),
    CONSTRAINT fk_support_order    FOREIGN KEY (order_id)    REFERENCES customer_order(id),
    CONSTRAINT fk_support_account  FOREIGN KEY (handled_by)  REFERENCES account(id),
    CONSTRAINT ck_support_status CHECK (status IN ('OPEN','IN_PROGRESS','RESOLVED'))
) ENGINE=InnoDB;

CREATE TABLE supplier (
    id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(120) NOT NULL,
    contact  VARCHAR(150)
) ENGINE=InnoDB;

CREATE TABLE restock_request (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id  BIGINT NOT NULL,
    supplier_id BIGINT NOT NULL,
    quantity    INT NOT NULL,
    status      VARCHAR(12) NOT NULL DEFAULT 'REQUESTED',
    created_by  BIGINT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_restock_product  FOREIGN KEY (product_id)  REFERENCES product(id),
    CONSTRAINT fk_restock_supplier FOREIGN KEY (supplier_id) REFERENCES supplier(id),
    CONSTRAINT fk_restock_account  FOREIGN KEY (created_by)  REFERENCES account(id),
    CONSTRAINT ck_restock_qty    CHECK (quantity > 0),
    CONSTRAINT ck_restock_status CHECK (status IN ('REQUESTED','CONFIRMED','RECEIVED','REJECTED'))
) ENGINE=InnoDB;

-- ---------- AI phase 2 (Chapter 3) ----------
CREATE TABLE interaction_log (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id  BIGINT,
    product_id   BIGINT,
    event_type   VARCHAR(15) NOT NULL,
    keyword      VARCHAR(150),
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_customer FOREIGN KEY (customer_id) REFERENCES customer(id),
    CONSTRAINT fk_log_product  FOREIGN KEY (product_id)  REFERENCES product(id),
    CONSTRAINT ck_log_event CHECK (event_type IN ('VIEW','SEARCH','ADD_TO_CART','PURCHASE','CLICK_REC','REC_IMPRESSION')),
    INDEX idx_log_customer (customer_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE product_embedding (
    product_id    BIGINT PRIMARY KEY,
    model         VARCHAR(60) NOT NULL,
    dim           INT NOT NULL,
    content_hash  CHAR(32) NOT NULL,                     -- re-embed only when the product text changed
    vector        BLOB NOT NULL,                         -- float32 vector for AI semantic search
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_product FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- Sample data  (passwords are set by seed.py because they must be hashed)
-- =====================================================================
INSERT INTO role(id,name) VALUES (1,'CUSTOMER'),(2,'ADMIN'),(3,'SERVICE'),(4,'SALES'),(5,'WAREHOUSE'),(6,'MARKETING'),(7,'MANAGER');

INSERT INTO account(id,email,password_hash,role_id) VALUES
 (1,'admin@abc.vn','CHANGE_ME',2),
 (2,'service@abc.vn','CHANGE_ME',3),
 (3,'warehouse@abc.vn','CHANGE_ME',5),
 (4,'an@gmail.com','CHANGE_ME',1),
 (5,'binh@gmail.com','CHANGE_ME',1);

INSERT INTO customer(id,first_name,middle_name,last_name,phone,loyalty_tier) VALUES
 (4,'An','Van','Nguyen','0901000001','NEW'),
 (5,'Binh',NULL,'Tran','0901000002','VIP');
INSERT INTO address(customer_id,recipient,phone,street,district,city,is_default) VALUES
 (4,'Nguyen Van An','0901000001','12 Tran Phu','Ha Dong','Ha Noi',TRUE);
INSERT INTO cart(customer_id) VALUES (4),(5);

INSERT INTO category(id,name,description) VALUES
 (1,'Books','Sach'),(2,'Electronics','Laptop, dien thoai'),(3,'Clothes','Thoi trang'),(4,'Shoes','Giay dep');

INSERT INTO product(id,category_id,sku,name,description,brand,price,attributes) VALUES
 (1,1,'BK-001','Clean Code','Robert C. Martin','Prentice Hall',350000,'{"isbn":"9780132350884","author":"Robert C. Martin"}'),
 (2,2,'LT-001','Laptop Pro 14','Laptop van phong','ABC',21500000,'{"cpu":"Core i5","ram":"16GB","storage":"512GB"}'),
 (3,2,'MB-001','Smartphone X','Dien thoai','XPhone',9900000,'{"screenSize":6.1,"storage":"128GB","warrantyMonths":12}'),
 (4,3,'CL-001','Ao so mi nam','Cotton','ABC',299000,'{"size":"M","color":"white","material":"cotton"}'),
 (5,4,'SH-001','Giay chay bo','Running shoes','RunFast',1250000,'{"shoesSize":42,"shoesType":"running"}'),
 (6,1,'BK-002','Database System Concepts','Silberschatz','McGraw-Hill',890000,'{"isbn":"9780078022159"}');

INSERT INTO inventory(product_id,quantity,min_threshold) SELECT id,20,5 FROM product;
UPDATE inventory SET quantity = 3 WHERE product_id = 5;   -- low-stock sample (below threshold)

INSERT INTO promotion(code,discount_type,discount_value,min_order_value,start_at,end_at)
 VALUES ('WELCOME10','PERCENT',10,200000,'2026-01-01 00:00:00','2026-12-31 23:59:59');
INSERT INTO supplier(name,contact) VALUES ('Nha cung cap A','a@supplier.vn');
