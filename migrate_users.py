import sqlite3

DB = "shop.db"   # shu joyda sen ishlatayotgan DB nomi bilan bir xil bo‘lishi kerak!

def add_column_if_not_exists(conn, table, column, coltype):
    cur = conn.cursor()
    # jadval ustunlarini tekshiramiz
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
        print(f"✅ Added {column} to {table}")

def main():
    conn = sqlite3.connect(DB)
    # Users jadvaliga yangi ustunlar qo‘shish
    add_column_if_not_exists(conn, "users", "phone", "TEXT")
    add_column_if_not_exists(conn, "users", "address", "TEXT")
    add_column_if_not_exists(conn, "users", "lat", "REAL")
    add_column_if_not_exists(conn, "users", "lon", "REAL")
    conn.commit()
    conn.close()
    print("🚀 Migration done.")

if __name__ == "__main__":
    main()