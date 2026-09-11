import sqlite3
from datetime import datetime

DB_PATH = "finance.db"

CATEGORIES = {
    "chiqim": ["Oziq-ovqat", "Transport", "Kommunal", "Kiyim-kechak", "Ko'ngilochar",
               "Sog'liq", "Ta'lim", "Boshqa"],
    "kirim": ["Ish haqi", "Qo'shimcha daromad", "Sovg'a", "Boshqa"],
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_transaction(user_id: int, t_type: str, amount: float, category: str, comment: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, type, amount, category, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, t_type, amount, category, comment, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_last_transaction(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM transactions WHERE id=?", (row[0],))
        conn.commit()
    conn.close()
    return row is not None


def get_balance(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='kirim'", (user_id,))
    kirim = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='chiqim'", (user_id,))
    chiqim = cur.fetchone()[0]
    conn.close()
    return kirim, chiqim, kirim - chiqim


def get_monthly_report(user_id: int, year: int, month: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    month_str = f"{year:04d}-{month:02d}"
    cur.execute(
        """
        SELECT type, category, SUM(amount), COUNT(*) FROM transactions
        WHERE user_id=? AND strftime('%Y-%m', created_at)=?
        GROUP BY type, category
        ORDER BY type DESC, SUM(amount) DESC
        """,
        (user_id, month_str),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_transactions(user_id: int, limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, type, amount, category, comment, created_at FROM transactions
        WHERE user_id=? ORDER BY id DESC LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
