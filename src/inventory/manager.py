import sqlite3
from src.inventory.database import get_connection
from src.inventory.product import Product

class InventoryManager:
    def __init__(self):
        pass
 
    def add_product(self, name: str, price: float, category: str, stock: int) -> Product:
        """Validates a product using your guard clauses and inserts it into SQLite."""
        # Enforce your custom model validations first
        product = Product(name, price, category, stock)
        
        query = """
        INSERT INTO products (name, price, category, stock) 
        VALUES (?, ?, ?, ?);
        """
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (product.name, product.price, product.category, product.stock))
            conn.commit()
            return product
        except sqlite3.IntegrityError:
            # Handles constraint failure if a duplicate product name is added
            raise ValueError(f"A product named '{product.name}' already exists.")
        finally:
            cursor.close()
            conn.close()
    
    def stock_in(self,name:str,quantity:int) -> bool:
        if quantity<=0:
            raise ValueError("Stock quantity must be a greater than 0.")
        
        conn=get_connection()
        cursor=conn.cursor()

        try:
            # Fetch name and current stock
            cursor.execute("SELECT name from products WHERE name=?",(name,))
            result = cursor.fetchone() # Returns a single tuple or None
            
            if not result:
                raise ValueError(f"Product '{name}' does not exist in inventory.")

            current_stock = result[1]
            new_stock = current_stock + quantity
        
            # Reuse your low-level helper to update the database
            success = self.update_product_stock(name, new_stock)
            return success
        finally:
            cursor.close()
            conn.close()

        
    def stock_out(self,name:str,quantity:int) -> bool:
        if quantity<=0:
            raise ValueError("Stock quantity must be a greater than 0.")
        
        conn=get_connection()
        cursor=conn.cursor()

        try:
            cursor.execute("SELECT name,stock from products WHERE name=?",(name,))
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"Product '{name}' does not exist in inventory.")
        
            if result[1]<quantity:
                raise ValueError(f"Insufficient stock for product '{name}'. Current stock: {result[1]}")
        
            new_stock=result[1]-quantity
        
            success=self.update_product_stock(name,new_stock)
            return success
        finally:
            cursor.close()
            conn.close()
    
    
    def get_all_products(self):
        """Retrieves rows from SQLite and reconstructs your Product objects."""
        query = "SELECT name, price, category, stock FROM products;"
        products_list = []
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                # Reconstruct your updated Product layout mapping row values cleanly
                prod = Product(name=row[0], price=row[1], category=row[2], stock=row[3])
                products_list.append(prod)
            return products_list
        finally:
            cursor.close()
            conn.close()

    def update_product_stock(self, name: str, stock: int) -> bool:
        """Updates the stock level using the product name as the unique target identifier."""
        if stock < 0:
            raise ValueError("Product stock level cannot be negative.")
            
        target_name = name.strip()
        query = "UPDATE products SET stock = ? WHERE name = ?;"
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (stock, target_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def delete_product_by_name(self, name: str) -> bool:
        """Deletes a product matching the specified name string identifier."""
        target_name = name.strip()
        query = "DELETE FROM products WHERE name = ?;"
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (target_name,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()