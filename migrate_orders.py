import sqlite3

DB_NAME = "shop.db"

def migrate():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # mavjud ustunlarni tekshirish
    cur.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cur.fetchall()]

    if "lat" not in columns:
        cur.execute("ALTER TABLE orders ADD COLUMN lat REAL")
        print("✅ lat ustuni qo‘shildi.")

    if "lon" not in columns:
        cur.execute("ALTER TABLE orders ADD COLUMN lon REAL")
        print("✅ lon ustuni qo‘shildi.")

    conn.commit()
    conn.close()
    print("🚀 Migration tugadi.")

if __name__ == "__main__":
    migrate()