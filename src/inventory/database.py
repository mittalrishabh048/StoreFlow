import sqlite3
import os

DB_PATH = "data/storeflow.db"

def get_connection():
    """Creates and returns a connection to the SQLite database file."""
    # Ensure the target directory exists before connecting
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)
    

def init_db():
    """Initializes the database schema and builds the products table."""
    connection = get_connection()
    cursor = connection.cursor()

    # Force SQLite to actively enforce Foreign Key constraints at runtime
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Core Inventory Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    # 2. Billing Sales Transaction Table (Receipt Headers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL
        )
    """)
    
    # 3. Transaction Item Line Breakdown Table (Receipt Rows)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_sale REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    
    connection.commit()
    connection.close()
    print("[DATABASE SUCCESS] All relational tables (products, sales, sale_items) initialized.")

if __name__ == "__main__":
    init_db()