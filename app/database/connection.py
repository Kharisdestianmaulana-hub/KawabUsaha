import sqlite3
from contextlib import contextmanager

# Untuk kemudahan MVP, kita simpan database di root folder
DB_PATH = 'kawanusaha.db'

@contextmanager
def get_db_connection():
    """Context manager untuk koneksi database SQLite."""
    conn = sqlite3.connect(DB_PATH)
    # Membuat hasil query dikembalikan seperti dictionary (bisa diakses via nama kolom)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
