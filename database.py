# database.py
import sqlite3
import logging

DATABASE_NAME = 'bot_users.db'
logger = logging.getLogger(__name__)

def get_db_connection():
    """Membuat koneksi ke database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Membuat tabel 'users' jika belum ada."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_authorized INTEGER DEFAULT 0,
                username TEXT,
                first_name TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database berhasil diinisialisasi.")
    except Exception as e:
        logger.error(f"Error saat inisialisasi database: {e}")

def is_user_authorized(user_id: int) -> bool:
    """Memeriksa apakah user_id diizinkan (is_authorized == 1)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_authorized FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result['is_authorized'] == 1:
            return True
        return False
    except Exception as e:
        logger.error(f"Error saat memeriksa otorisasi user {user_id}: {e}")
        return False

def set_user_access(user_id: int, status: bool, username: str = None, first_name: str = None):
    """Memberi atau mencabut akses pengguna. Juga menambahkan user jika belum ada."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # INSERT OR IGNORE untuk menambahkan user baru tanpa error jika sudah ada
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        # UPDATE untuk mengatur status otorisasi
        cursor.execute(
            "UPDATE users SET is_authorized = ?, username = ?, first_name = ? WHERE user_id = ?",
            (1 if status else 0, username, first_name, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Akses untuk user {user_id} diatur ke {status}.")
    except Exception as e:
        logger.error(f"Error saat mengatur akses user {user_id}: {e}")

def get_user_count() -> int:
    """Menghitung jumlah total pengguna yang terdaftar (diizinkan atau tidak)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error saat menghitung user: {e}")
        return 0

# Dummy function, karena di kode utama Anda ada `add_user`
def add_user(user_id: int, username: str, first_name: str):
    """Fungsi ini sekarang hanya memanggil set_user_access tanpa memberi otorisasi."""
    set_user_access(user_id, False, username, first_name)
