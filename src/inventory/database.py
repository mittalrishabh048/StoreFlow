import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Step up two directory levels to reach STOREFLOW, then descend straight into the data/ directory!
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../data/storeflow.db"))

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

    #2. Billing Sales Transaction Table (Receipt Headers)
    # Force a reset of the old table layout so the new columns populate correctly
    cursor.execute("DROP TABLE IF EXISTS sale_items;")
    cursor.execute("DROP TABLE IF EXISTS sales;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
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

def get_latest_invoice_number(db_path=DB_PATH):
    """
    Queries the database for the highest/most recent invoice number 
    to figure out the next sequential ID.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Assuming our sales/invoice table holds the invoice_number column
        cursor.execute("SELECT invoice_number FROM sales ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        return None
    finally:
        conn.close()

def save_invoice_transaction(invoice_number, cart_items, total_amount, db_path=DB_PATH):
    """
    Executes an atomic database transaction to record the invoice 
    and save snapshot pricing values to preserve history.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("BEGIN TRANSACTION;")
    cursor = conn.cursor()
    try:
        # FIXED: Explicitly targeting your timestamp column matching init_db
        cursor.execute(
            "INSERT INTO sales (invoice_number, total_amount, timestamp) VALUES (?, ?, datetime('now', 'localtime'))",
            (invoice_number, total_amount)
        )
        sale_id = cursor.lastrowid

        for item in cart_items:
            p_id, qty, price, tax = item
            
            # Save historical snapshot data using your structural schema column name (price_at_sale)
            cursor.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                (sale_id, p_id, qty, price)
            )
            
            # Atomic stock deduction
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?", 
                (qty, p_id)
            )
            
        conn.commit()
        return sale_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_invoices(db_path=DB_PATH):
    """
    Queries the database for all recorded master invoices, 
    sorting them chronologically from newest to oldest.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Sort newest first using DESC on the primary key index or timestamp
        cursor.execute("SELECT id, invoice_number, timestamp, total_amount FROM sales ORDER BY id DESC")
        rows = cursor.fetchall()
        
        invoices_list = []
        for row in rows:
            invoices_list.append({
                "sale_id": row["id"],
                "invoice_number": row["invoice_number"],
                "timestamp": row["timestamp"],
                "grand_total": row["total_amount"]
            })
        return invoices_list
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()