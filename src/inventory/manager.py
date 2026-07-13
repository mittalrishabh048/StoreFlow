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
    
    def update_product(self,name:str, new_price:float, new_category:str, new_stock:int)->bool:
        """Updates the price, category, and stock fields of an existing product by its name."""
        # 1. Enforce business logic guard clauses
        if new_price < 0.0:
            raise ValueError("Product price cannot be negative.")
        if new_stock < 0:
            raise ValueError("Product stock level cannot be negative.")
        if not new_category.strip():
            raise ValueError("Product category cannot be empty.")
        
        target_name = name.strip()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE products SET price=?,category=?,stock=? where name=?", (new_price, new_category.strip(), new_stock, target_name))
            conn.commit()
            # Returns True if the row count changed (product found and updated)
            return cursor.rowcount > 0
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
            cursor.execute("SELECT name,stock from products WHERE name=?",(name.strip(),))
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
        query = "SELECT id,name, price, category, stock FROM products"
        products_list = []
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                # Reconstruct your updated Product layout mapping row values cleanly
                prod = Product(id=row[0],name=row[1], price=row[2], category=row[3], stock=row[4])
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

    def delete_product(self, name: str) -> bool:
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

    def get_low_stocks_alert(self,threshold:int)->list[Product]:
        """Retrieves all product records where stock falls below a specified threshold."""
        self.threshold=threshold

        low_stock_products=[]

        conn=get_connection()
        cursor=conn.cursor()
        
        try:
            cursor.execute("SELECT name,price,category,stock from products WHERE stock<=?",(threshold,))
            results=cursor.fetchall()
            for row in results:
                prod=Product(name=row[0], price=row[1], category=row[2], stock=row[3])
                low_stock_products.append(prod)
            return low_stock_products
        finally:
            cursor.close()
            conn.close()


    def search_products(self,keyword:str)-> list[Product]:
        # Wrap the search term in % wildcards for partial matching
        search_term = f"%{keyword.strip()}%"

        products_list = []
        
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name,price,category,stock from products WHERE name LIKE ? OR category LIKE ?", (search_term, search_term))
            results=cursor.fetchall()
            for row in results:
                prod = Product(name=row[0], price=row[1], category=row[2], stock=row[3])
                products_list.append(prod)
            return products_list
        
        finally:
            cursor.close()
            conn.close()

    def get_inventory_summary(self)->dict:
        """Calculates overarching inventory statistics directly inside the database engine."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(id),SUM(price*stock) FROM products")
            results=cursor.fetchone()
            
            total_products = results[0] if results[0] else 0
            total_value = results[1] if results[1] else 0.0

            return {
                "total_products": total_products,
                "total_value": total_value
            }
        
        finally:
            cursor.close()
            conn.close()

    def get_todays_revenue(self):
        """1. Helper method for today's active transaction revenue."""
        from src.inventory import database
        kpis = database.get_dashboard_kpis()
        return kpis["revenue"]

    def get_todays_sales_count(self):
        """2. Helper method for today's total active orders count."""
        from src.inventory import database
        kpis = database.get_dashboard_kpis()
        return kpis["sales_count"]

    def get_todays_units_sold(self):
        """3. Helper method for today's aggregate inventory units sold."""
        from src.inventory import database
        kpis = database.get_dashboard_kpis()
        return kpis["units_sold"]

    def get_top_5_products(self):
        """4. Helper method for the top 5 best-selling products panel."""
        from src.inventory import database
        return database.get_top_selling_products(limit=5)

    def get_7_day_revenue_summary(self):
        """5. Helper method for the 7-day chronological revenue summary trends."""
        from src.inventory import database
        return database.get_seven_day_revenue_summary()

    def get_low_stock_count(self):
        """6. Helper method for low-stock widget tracking count."""
        from src.inventory import database
        # Reuses the warning array to calculate the total count of endangered products
        alerts = database.get_low_stock_alerts(threshold=5)
        return len(alerts)

    def get_low_stock_items(self):
        """7. Additional helper method to pull the detailed low-stock items list."""
        from src.inventory import database
        return database.get_low_stock_alerts(threshold=5)

    def generate_inventory_report(self):
        """Processes product details and aggregates global warehouse financial values."""
        from src.inventory import database
        raw_items = database.get_inventory_report_data()
        
        processed_products = []
        grand_total_value = 0.0
        
        for item in raw_items:
            line_value = round(item["stock"] * item["price"], 2)
            grand_total_value += line_value
            processed_products.append({
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "price": item["price"],
                "stock": item["stock"],
                "total_value": line_value
            })
            
        return {
            "products": processed_products,
            "grand_total": round(grand_total_value, 2)
        }

    def generate_sales_report(self, start_date=None, end_date=None):
        """Calculates revenue run-rates, order volume counts, and overall transactional averages."""
        from src.inventory import database
        orders = database.get_sales_report_data(start_date, end_date)
        
        total_revenue = sum(order["total_amount"] for order in orders)
        total_transactions = len(orders)
        
        # Guard against division by zero if no sales exist inside the boundary parameters
        avg_order_value = round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0.0
        
        return {
            "orders": orders,
            "total_revenue": round(total_revenue, 2),
            "total_transactions": total_transactions,
            "avg_order_value": avg_order_value
        }

    def generate_inventory_csv(self):
        """Builds a formatted CSV text stream summarizing active product capital assets."""
        import csv
        import io
        
        # Pull live product data metrics
        report_data = self.generate_inventory_report()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write structural header line metadata
        writer.writerow(["Product ID", "Product Name", "Category", "Unit Price (Rs.)", "Available Stock", "Total Valuation (Rs.)"])
        
        # Write data breakdown rows
        for p in report_data["products"]:
            writer.writerow([p["id"], p["name"], p["category"], f"{p['price']:.2f}", p["stock"], f"{p['total_value']:.2f}"])
            
        # Write summation footer block
        writer.writerow([])
        writer.writerow(["", "", "", "", "Grand Total Value:", f"{report_data['grand_total']:.2f}"])
        
        return output.getvalue()

    def generate_sales_csv(self, start_date=None, end_date=None):
        """Constructs a formatted CSV text stream bounded by calendar search constraints."""
        import csv
        import io
        
        # Pull transactional history matching parameters
        report_data = self.generate_sales_report(start_date, end_date)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header metadata
        writer.writerow(["Invoice Number", "Execution Timestamp", "Settled Amount (Rs.)"])
        
        # Write data rows
        for o in report_data["orders"]:
            writer.writerow([o["invoice_number"], o["timestamp"], f"{o['total_amount']:.2f}"])
            
        # Write statistical operational summary footer block
        writer.writerow([])
        writer.writerow(["Total Orders Count:", report_data["total_transactions"], ""])
        writer.writerow(["Total Billed Revenue:", f"{report_data['total_revenue']:.2f}", ""])
        writer.writerow(["Average Basket Ticket Value:", f"{report_data['avg_order_value']:.2f}", ""])
        
        return output.getvalue()

    def authenticate_user(self, username, plain_password):
        """
        Validates login parameters by retrieving the target record 
        and passing it through cryptographic verification checks.
        """
        from src.inventory import database
        from werkzeug.security import check_password_hash
        
        user = database.get_user_by_username(username.strip())
        if not user:
            return False, "Invalid username configuration entered."
            
        # Verify incoming plain text against the salted cryptographic hash string
        if check_password_hash(user["password"], plain_password):
            return True, "Authentication verified successfully."
            
        return False, "Incorrect security credential password provided."

    def get_system_settings(self):
        """Retrieves and processes configuration options from the database storage layer."""
        from src.inventory import database
        raw_settings = database.get_all_settings()
        
        # Enforce clean string fallbacks and correct numeric type casting formats
        return {
            "store_name": raw_settings.get("store_name", "StoreFlow Retail"),
            "address": raw_settings.get("address", ""),
            "phone": raw_settings.get("phone", ""),
            "email": raw_settings.get("email", ""),
            "currency": raw_settings.get("currency", "Rs."),
            "tax_rate": float(raw_settings.get("tax_rate", 0.00)),
            "low_stock_threshold": int(raw_settings.get("low_stock_threshold", 5))
        }

    def update_system_settings(self, settings_dict):
        """Validates configuration items and updates values in the database layer."""
        from src.inventory import database
        
        # 1. Enforce numerical check validation boundaries
        try:
            tax = float(settings_dict.get("tax_rate", 0.0))
            if tax < 0: raise ValueError
        except (ValueError, TypeError):
            return False, "Tax rate parameter must be a valid non-negative decimal value."
            
        try:
            threshold = int(settings_dict.get("low_stock_threshold", 5))
            if threshold < 0: raise ValueError
        except (ValueError, TypeError):
            return False, "Low stock warning threshold parameter must be a positive integer."

        # 2. Push validated settings out using the database helper functions
        database.save_setting_value("store_name", settings_dict.get("store_name", "").strip())
        database.save_setting_value("address", settings_dict.get("address", "").strip())
        database.save_setting_value("phone", settings_dict.get("phone", "").strip())
        database.save_setting_value("email", settings_dict.get("email", "").strip())
        database.save_setting_value("currency", settings_dict.get("currency", "Rs.").strip())
        database.save_setting_value("tax_rate", tax)
        database.save_setting_value("low_stock_threshold", threshold)
        
        return True, "Configuration metrics modified successfully."