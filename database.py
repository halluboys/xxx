# File: database.py

import sqlite3
import logging

# Konfigurasi logging dasar
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_FILE = "bot_users.db"

def initialize_database():
    """Membuat file database dan tabel 'users' jika belum ada."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    # Skema tabel yang sudah diperbarui dengan kolom 'is_authorized'
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_authorized BOOLEAN DEFAULT 0
        )
    """)
    
    con.commit()
    con.close()
    logger.info(f"Database '{DB_FILE}' berhasil diinisialisasi atau sudah ada.")

def add_user(user_id: int, username: str, first_name: str):
    """Menambahkan pengguna baru ke database. Mengabaikan jika user_id sudah ada."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        con.commit()
        logger.info(f"User {user_id} ditambahkan ke database (jika belum ada).")
    finally:
        con.close()

def get_user_count() -> int:
    """Menghitung jumlah total pengguna di database."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        return count
    finally:
        con.close()

def set_user_access(user_id: int, authorized: bool):
    """Mengatur status akses seorang pengguna (1 untuk True, 0 untuk False)."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        # Konversi boolean ke integer (1 atau 0) untuk SQLite
        auth_status = 1 if authorized else 0
        cur.execute("UPDATE users SET is_authorized = ? WHERE user_id = ?", (auth_status, user_id))
        con.commit()
        logger.info(f"Status akses untuk user {user_id} diubah menjadi {authorized}.")
    finally:
        con.close()

def is_user_authorized(user_id: int) -> bool:
    """Mengecek apakah seorang pengguna diizinkan akses."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        cur.execute("SELECT is_authorized FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if result and result[0] == 1:
            return True
        return False
    finally:
        con.close()
