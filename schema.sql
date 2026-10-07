-- =====================================================================
-- MULTIMODAL E-COMMERCE SEARCH SYSTEM (ASSIGNMENT 05 & 06)
-- Database Setup Script for MySQL Workbench
-- =====================================================================

-- 1. Create Database if not exists
CREATE DATABASE IF NOT EXISTS multimodal_search_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE multimodal_search_db;

-- 2. Drop existing tables in correct foreign key order
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;

-- 3. Create Products Table
-- Stores product specifications, pricing, inventory stock, and vector embeddings
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    color VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    stock INT NOT NULL DEFAULT 0,
    description TEXT,
    image VARCHAR(255),
    embedding JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Create Orders Table
-- Stores customer orders, timestamps, delivery status, and order totals
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Processing',
    total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Create Order Items Table
-- Stores line items associated with each order (Foreign Keys to orders and products)
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(50) NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- SEED DATA INSERTION
-- =====================================================================

-- Insert 12 initial products with 3D image vector embeddings
INSERT INTO products (id, name, category, color, price, stock, description, image, embedding) VALUES
(1, 'Nike Running Shoes', 'shoes', 'black', 120.00, 10, 'High performance black running shoes with responsive cushioning.', 'images/nike_running_black.png', '[0.9, 0.1, 0.2]'),
(2, 'Adidas Running Shoes', 'shoes', 'white', 100.00, 15, 'Lightweight white running shoes designed for marathon endurance.', 'images/adidas_running_white.png', '[0.2, 0.8, 0.1]'),
(3, 'Black Leather Bag', 'bag', 'black', 80.00, 20, 'Premium black leather bag suitable for work and casual travel.', 'images/black_leather_bag.png', '[0.1, 0.2, 0.9]'),
(4, 'Blue Sports Shoes', 'shoes', 'blue', 75.00, 12, 'Comfortable blue sports shoes ideal for gym workouts and training.', 'images/blue_sports_shoes.png', '[0.8, 0.2, 0.2]'),
(5, 'Puma Trail Running Shoes', 'shoes', 'black', 90.00, 8, 'Rugged black trail running shoes with enhanced grip outsole.', 'images/puma_trail_black.png', '[0.85, 0.15, 0.25]'),
(6, 'Brown Leather Crossbody Bag', 'bag', 'brown', 95.00, 5, 'Classic brown genuine leather crossbody bag with multiple compartments.', 'images/brown_leather_crossbody.png', '[0.12, 0.3, 0.85]'),
(7, 'Red Canvas Sneakers', 'shoes', 'red', 60.00, 18, 'Casual red canvas low-top sneakers for everyday street style.', 'images/red_canvas_sneakers.png', '[0.75, 0.35, 0.15]'),
(8, 'White Casual T-Shirt', 'clothing', 'white', 25.00, 50, 'Breathable 100% organic cotton white t-shirt for casual wear.', 'images/white_casual_tshirt.png', '[0.3, 0.7, 0.4]'),
(9, 'Black Formal Leather Shoes', 'shoes', 'black', 140.00, 7, 'Elegant handcrafted black leather oxford shoes for formal events.', 'images/black_formal_oxford.png', '[0.6, 0.2, 0.75]'),
(10, 'Waterproof Hiking Backpack', 'bag', 'black', 110.00, 14, 'Heavy-duty waterproof black outdoor backpack for trekking and hiking.', 'images/waterproof_backpack_black.png', '[0.35, 0.25, 0.88]'),
(11, 'Green Athletic Running Shorts', 'clothing', 'green', 35.00, 25, 'Lightweight quick-dry green running shorts with reflective elements.', 'images/green_running_shorts.png', '[0.5, 0.6, 0.3]'),
(12, 'Smart Fitness Watch', 'accessories', 'black', 150.00, 0, 'Advanced black digital smartwatch with heart-rate and GPS tracking.', 'images/smart_fitness_watch.png', '[0.4, 0.5, 0.6]');

-- Insert sample customer orders
INSERT INTO orders (order_id, customer_id, order_date, status, total) VALUES
('O001', 'C001', '2026-09-25', 'Shipped', 150.00),
('O002', 'C002', '2026-09-28', 'Delivered', 80.00),
('O003', 'C001', '2026-09-30', 'Processing', 175.00),
('20261001', 'C003', '2026-10-01', 'Out for Delivery', 90.00);

-- Insert items for each order
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
('O001', 1, 1, 120.00),
('O002', 3, 1, 80.00),
('O003', 2, 1, 100.00),
('O003', 4, 1, 75.00),
('20261001', 5, 1, 90.00);

-- Verify data
SELECT 'Products Count:' AS CheckLabel, COUNT(*) AS Total FROM products
UNION ALL
SELECT 'Orders Count:', COUNT(*) FROM orders
UNION ALL
SELECT 'Order Items Count:', COUNT(*) FROM order_items;
