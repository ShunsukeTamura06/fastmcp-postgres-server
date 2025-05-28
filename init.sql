-- PostgreSQL MCP Server テスト用サンプルデータ

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    age INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 製品テーブル
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 注文テーブル
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 注文明細テーブル
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- サンプルデータの挿入
INSERT INTO users (name, email, age) VALUES
    ('田中太郎', 'tanaka@example.com', 30),
    ('佐藤花子', 'sato@example.com', 25),
    ('鈴木一郎', 'suzuki@example.com', 35),
    ('山田美咲', 'yamada@example.com', 28)
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (name, price, category, description, stock_quantity) VALUES
    ('ノートパソコン', 89800.00, 'electronics', '高性能ノートパソコン', 50),
    ('スマートフォン', 78900.00, 'electronics', '最新モデル', 100),
    ('コーヒーメーカー', 12800.00, 'appliances', '全自動コーヒーメーカー', 30),
    ('デスクチェア', 25900.00, 'furniture', '人間工学に基づいた設計', 20),
    ('プログラミング本', 3980.00, 'books', 'Python入門書', 75)
ON CONFLICT DO NOTHING;

INSERT INTO orders (user_id, total_amount, status) VALUES
    (1, 89800.00, 'completed'),
    (2, 78900.00, 'pending'),
    (3, 38880.00, 'completed'),
    (1, 25900.00, 'shipped')
ON CONFLICT DO NOTHING;

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
    (1, 1, 1, 89800.00),
    (2, 2, 1, 78900.00),
    (3, 3, 1, 12800.00),
    (3, 4, 1, 25900.00),
    (3, 5, 1, 3980.00),
    (4, 4, 1, 25900.00)
ON CONFLICT DO NOTHING;

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- ビューの作成（複雑なクエリのテスト用）
CREATE OR REPLACE VIEW order_summary AS
SELECT 
    o.id as order_id,
    u.name as customer_name,
    u.email as customer_email,
    o.total_amount,
    o.status,
    o.order_date,
    COUNT(oi.id) as item_count
FROM orders o
JOIN users u ON o.user_id = u.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id, u.name, u.email, o.total_amount, o.status, o.order_date
ORDER BY o.order_date DESC;