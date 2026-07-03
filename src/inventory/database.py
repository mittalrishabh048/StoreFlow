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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    connection.commit()
    connection.close()