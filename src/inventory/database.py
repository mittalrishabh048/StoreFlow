import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Securely hash the baseline default password string 'admin123'
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_pw))
        print("[DATABASE SUCCESS] Default admin user successfully seeded.")

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

def get_all_invoices(date_from=None, date_to=None, product_name=None, db_path=DB_PATH):
    """
    Queries the database for master invoices, dynamically applying 
    safe parameterized filters for dates and product names.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Base query pulls distinct sales headers (handles duplicates from product JOINs)
        query = """
            SELECT DISTINCT s.id, s.invoice_number, s.timestamp, s.total_amount,s.status
            FROM sales s
        """
        
        # If filtering by product name, we must JOIN with the breakdown tables
        if product_name:
            query += """
                JOIN sale_items si ON s.id = si.sale_id
                JOIN products p ON si.product_id = p.id
            """
            
        where_clauses = []
        params = []
        
        # Apply Start Date criteria
        if date_from:
            where_clauses.append("s.timestamp >= ?")
            params.append(f"{date_from} 00:00:00")
            
        # Apply End Date criteria
        if date_to:
            where_clauses.append("s.timestamp <= ?")
            params.append(f"{date_to} 23:59:59")
            
        # Apply Wildcard Product Name criteria
        if product_name:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{product_name}%")
            
        # Append combined WHERE constraints if filters exist
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        # Maintain chronologically ordered sorting layout
        query += " ORDER BY s.id DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        invoices_list = []
        for row in rows:
            invoices_list.append({
                "sale_id": row["id"],
                "invoice_number": row["invoice_number"],
                "timestamp": row["timestamp"],
                "grand_total": row["total_amount"],
                "status": row["status"] # FIXED: Pass the status to the template
            })
        return invoices_list
        
    finally:
        conn.close()

def void_sale_transaction(sale_id, db_path=DB_PATH):
    """
    Validates a transaction status, restores item quantities to product inventory, 
    and sets the master record state to 'VOID' atomically.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN TRANSACTION;")
    cursor = conn.cursor()
    
    try:
        # 1. Validate invoice existence and active status state
        cursor.execute("SELECT status FROM sales WHERE id = ?", (sale_id,))
        sale = cursor.fetchone()
        
        if not sale:
            conn.close()
            return False, "Target sale reference record could not be found."
        if sale["status"] == "VOID":
            conn.close()
            return False, "This transaction has already been voided."
            
        # 2. Gather item lists linked to this sale to calculate inventory restoration values
        cursor.execute("SELECT product_id, quantity FROM sale_items WHERE sale_id = ?", (sale_id,))
        items = cursor.fetchall()
        
        # 3. Process restoration loops across inventory catalog models
        for item in items:
            cursor.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"])
            )
            
        # 4. Flip master record audit flag safely
        cursor.execute("UPDATE sales SET status = 'VOID' WHERE id = ?", (sale_id,))
        
        conn.commit()
        return True, "Sale transaction successfully voided and stock restored."
        
    except Exception as e:
        conn.rollback()
        return False, f"Critical rollback handled during voiding: {str(e)}"
    finally:
        conn.close()

def get_daily_summary_stats(db_path=DB_PATH):
    """
    Uses SQL aggregation functions to compute today's total revenue 
    and transaction count for all non-voided sales.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # We aggregate only ACTIVE records processed on the current calendar date
        cursor.execute("""
            SELECT 
                COALESCE(SUM(total_amount), 0.0), 
                COUNT(id) 
            FROM sales 
            WHERE status = 'ACTIVE' AND date(timestamp) = date('now', 'localtime')
        """)
        row = cursor.fetchone()
        return {
            "revenue": row[0],
            "count": row[1]
        }
    finally:
        conn.close()

def get_dashboard_kpis(db_path=DB_PATH):
    """
    Computes today's core operational metrics: Revenue, Sales Volume, 
    and total individual units moved, ignoring voided transactions.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # 1. Today's Revenue & Sales Count
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0), COUNT(id)
            FROM sales
            WHERE status = 'ACTIVE' AND date(timestamp) = date('now', 'localtime')
        """)
        rev_row = cursor.fetchone()
        today_revenue = rev_row[0]
        today_sales_count = rev_row[1]

        # 2. Today's Total Units Sold
        cursor.execute("""
            SELECT COALESCE(SUM(si.quantity), 0)
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE s.status = 'ACTIVE' AND date(s.timestamp) = date('now', 'localtime')
        """)
        today_units_sold = cursor.fetchone()[0]

        return {
            "revenue": today_revenue,
            "sales_count": today_sales_count,
            "units_sold": today_units_sold
        }
    finally:
        conn.close()


def get_low_stock_alerts(threshold=5, db_path=DB_PATH):
    """
    Scans the inventory registry for any items whose remaining quantity 
    has dropped below the critical threshold level.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, stock FROM products WHERE stock <= ?", (threshold,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_top_selling_products(limit=5, db_path=DB_PATH):
    """
    Aggregates overall unit sales numbers per product to extract the 
    top-performing inventory catalog items.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.name, SUM(si.quantity) as total_qty, SUM(si.quantity * si.price_at_sale) as total_sales
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sale_id = s.id
            WHERE s.status = 'ACTIVE'
            GROUP BY si.product_id
            ORDER BY total_qty DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_seven_day_revenue_summary(db_path=DB_PATH):
    """
    Generates a daily breakdown list spanning the last 7 calendar days 
    to construct chronological sales trend lines.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Generates a rolling window of the past 7 days dynamically via SQL date offsets
        cursor.execute("""
            SELECT date(timestamp) as sale_date, COALESCE(SUM(total_amount), 0.0) as daily_revenue
            FROM sales
            WHERE status = 'ACTIVE' AND date(timestamp) >= date('now', '-6 days', 'localtime')
            GROUP BY sale_date
            ORDER BY sale_date DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_inventory_report_data(db_path=DB_PATH):
    """Queries the complete list of inventory items to build financial valuation metrics."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, category, price, stock FROM products ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_sales_report_data(start_date=None, end_date=None, db_path=DB_PATH):
    """Retrieves transactional logs bounded by optional calendar parameters, omitting voids."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        query = "SELECT id, invoice_number, timestamp, total_amount FROM sales WHERE status = 'ACTIVE'"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND timestamp <= ?"
            params.append(f"{end_date} 23:59:59")
            
        query += " ORDER BY id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_user_by_username(username, db_path=DB_PATH):
    """Queries the user records table for a matching username string profile."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()