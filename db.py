import sqlite3
from datetime import datetime
import pytz

DB_NAME = "shop.db"   # 📂 Shu nom bilan DB ishlatiladi

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.row_factory = sqlite3.Row  # dict-like (row['name']) ishlatish uchun
    return conn

# =====================
# 📦 DB INIT
# =====================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 👤 Users jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id TEXT UNIQUE,
        name TEXT,
        phone TEXT,
        address TEXT,
        lat REAL,
        lon REAL,
        lang TEXT DEFAULT 'uz'
    )
    """)

    # 📦 Orders jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id TEXT,
        name TEXT,
        phone TEXT,
        address TEXT,
        total_price REAL,
        receipt TEXT,
        status TEXT DEFAULT 'Kutilmoqda',
        created_at TEXT
    )
    """)

    # 📦 Order_items jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )
    """)

    # 📦 Categories jadvali (UZ/RU qo'llab-quvvatlash bilan)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_uz TEXT,
        name_ru TEXT
    )
    """)

    # 📦 Products jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        category_id INTEGER,
        image TEXT,
        stock INTEGER DEFAULT 100,
        is_available INTEGER DEFAULT 1,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """)

    conn.commit()

    # Mavjud jadvalga yangi ustunlar qo'shish (migratsiya)
    cur.execute("PRAGMA table_info(products)")
    cols = [r[1] for r in cur.fetchall()]
    if "stock" not in cols:
        cur.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 100")
    if "is_available" not in cols:
        cur.execute("ALTER TABLE products ADD COLUMN is_available INTEGER DEFAULT 1")

    conn.commit()
    conn.close()

# =====================
# 👤 Users
# =====================
def get_user_by_tg_id(tg_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id=?", (str(tg_id),))
    user = cur.fetchone()
    conn.close()
    return user

def add_user(tg_id, name, phone=None, address=None, lat=None, lon=None, lang="uz"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (tg_id, name, phone, address, lat, lon, lang)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(tg_id), name, phone, address, lat, lon, lang))
    conn.commit()
    conn.close()

def update_user_lang(tg_id, lang):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, str(tg_id)))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY id DESC")
    users = cur.fetchall()
    conn.close()
    return users

# =====================
# 🧾 Orders
# =====================
def add_order(tg_id, name, phone, address, total_price, receipt=None, status="Kutilmoqda"):
    # 🇺🇿 Asia/Tashkent vaqtini olish
    tz = pytz.timezone("Asia/Tashkent")
    created_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (tg_id, name, phone, address, total_price, receipt, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(tg_id), name, phone, address, total_price, receipt, status, created_at))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_orders_by_user(tg_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE tg_id=? ORDER BY id DESC", (str(tg_id),))
    orders = cur.fetchall()

    result = []
    for o in orders:
        cur.execute("SELECT product_name, quantity, price FROM order_items WHERE order_id=?", (o["id"],))
        items = cur.fetchall()
        result.append({**dict(o), "items": [dict(i) for i in items]})

    conn.close()
    return result

def get_all_orders_with_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cur.fetchall()

    result = []
    for o in orders:
        cur.execute("SELECT product_name, quantity, price FROM order_items WHERE order_id=?", (o["id"],))
        items = cur.fetchall()
        result.append({**dict(o), "items": [dict(i) for i in items]})

    conn.close()
    return result

def get_all_orders():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cur.fetchall()
    conn.close()
    return orders

# =====================
# 📂 Categories (UZ/RU)
# =====================
def get_all_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id ASC")
    categories = cur.fetchall()
    conn.close()
    return categories

def add_category(name_uz, name_ru=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (name_uz, name_ru) VALUES (?, ?)", (name_uz, name_ru))
    conn.commit()
    conn.close()

def update_category(category_id, name_uz, name_ru):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE categories SET name_uz=?, name_ru=? WHERE id=?", (name_uz, name_ru, category_id))
    conn.commit()
    conn.close()

def delete_category(category_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id=?", (category_id,))
    conn.commit()
    conn.close()