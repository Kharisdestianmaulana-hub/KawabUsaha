import sqlite3
from app.database.connection import get_db_connection

def run_migrations():
    """Fungsi ini akan dijalankan saat bot pertama kali menyala untuk membuat tabel jika belum ada."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabel Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,         -- Menggunakan Telegram User ID
                first_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabel Businesses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabel Products
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (id)
            )
        ''')
        
        # Tabel Inventory Transactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Sales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                total_amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Sale Items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                price_at_sale REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Customers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                name TEXT NOT NULL,
                phone TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE
            )
        ''')
        
        # Coba tambahkan kolom customer_id ke tabel sales jika belum ada
        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL")
        except sqlite3.OperationalError:
            pass # Kolom sudah ada
            
        # Coba tambahkan kolom pengaturan ke tabel businesses
        try:
            cursor.execute("ALTER TABLE businesses ADD COLUMN phone TEXT")
            cursor.execute("ALTER TABLE businesses ADD COLUMN address TEXT")
            cursor.execute("ALTER TABLE businesses ADD COLUMN currency TEXT DEFAULT 'Rp'")
            cursor.execute("ALTER TABLE businesses ADD COLUMN low_stock_threshold INTEGER DEFAULT 5")
        except sqlite3.OperationalError:
            pass # Kolom sudah ada
            
        # V2.0 Updates
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'Umum'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN staff_name TEXT DEFAULT 'Owner'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE businesses ADD COLUMN invite_code TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE businesses ADD COLUMN payment_methods TEXT DEFAULT 'Tunai,QRIS'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN discount INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Tunai'")
        except sqlite3.OperationalError:
            pass
            
        # Tabel Expenses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Staff
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                telegram_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'kasir',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Penghutang (Debtors)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS debtors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
            )
        ''')
        
        # Tabel Transaksi Hutang
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS debt_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debtor_id INTEGER,
                type TEXT NOT NULL, -- 'DEBT' atau 'PAYMENT'
                amount INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (debtor_id) REFERENCES debtors(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
