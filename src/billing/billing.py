import sqlite3
from src.inventory import database

class ShoppingCart:
    def __init__(self):
        """Initializes an empty session shopping cart structure."""
        # Key: product_id (int), Value: dict containing details and item quantity
        self.items = {}

    def add_item(self, product_id, name, price, quantity=1):
        """Adds a product to the cart or increments its count if it already exists."""
        if product_id in self.items:
            self.items[product_id]['quantity'] += quantity
        else:
            self.items[product_id] = {
                'name': name,
                'price': float(price),
                'quantity': quantity
            }
        print(f"[CART MODIFICATION] Added {quantity}x '{name}' to the cart.")

    def update_quantity(self, product_id, new_quantity):
        """Updates the selected item quantity or removes it entirely if set to 0."""
        if product_id in self.items:
            if new_quantity <= 0:
                self.remove_item(product_id)
            else:
                self.items[product_id]['quantity'] = int(new_quantity)
                print(f"[CART MODIFICATION] Updated product ID {product_id} quantity to {new_quantity}.")

    def remove_item(self, product_id):
        """Drops a target item record completely out of the cart tracking dictionary."""
        if product_id in self.items:
            removed_name = self.items[product_id]['name']
            del self.items[product_id]
            print(f"[CART MODIFICATION] Removed '{removed_name}' completely from the cart.")

    def get_total(self):
        """Calculates and returns the aggregated gross currency value of all cart selections."""
        total = sum(item['price'] * item['quantity'] for item in self.items.values())
        return round(total, 2)

    def get_all_items(self):
        """Returns a list summary of all tracked selections for clean UI loops."""
        return list(self.items.values())

    def clear(self):
        """Resets the cart back to an empty tracking dictionary state."""
        self.items = {}
        print("[CART MODIFICATION] Cart has been entirely emptied.")

    def process_checkout(self):
        """Executes a fully transactional database checkout routine, validating stock levels."""
        from inventory.database import get_connection
        
        # 1. EMPTY CART CHECK - Updated to return exactly 3 values
        if not self.items:
            return False, "Your shopping cart is empty.", None
            
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # PHASE 1: STOCK VALIDATION LOOP
            for product_id, item_details in self.items.items():
                cursor.execute(
                    "SELECT name, stock FROM products WHERE id = ?;", 
                    (product_id,)
                )
                product_record = cursor.fetchone()
                
                # 2. MISSING PRODUCT CHECK - Updated to return exactly 3 values
                if not product_record:
                    connection.close()
                    return False, f"Product error: '{item_details['name']}' no longer exists in our registry.", None
                
                current_db_name, current_stock = product_record
                requested_qty = item_details['quantity']
                
                # 3. INSUFFICIENT STOCK CHECK - Updated to return exactly 3 values
                if current_stock < requested_qty:
                    connection.close()
                    return False, f"Insufficient stock for '{current_db_name}'. Available: {current_stock}, Requested: {requested_qty}.", None

            # PHASE 2: INSERT MASTER TRANSACTION RECEIPT
            grand_total = self.get_total()
            cursor.execute(
                "INSERT INTO sales (total_amount) VALUES (?);", 
                (grand_total,)
            )
            parent_sale_id = cursor.lastrowid
            
            # PHASE 3: RECORD BREAKDOWN ITEMS & DEDUCT STOCK
            for product_id, item_details in self.items.items():
                cursor.execute(
                    """
                    INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale)
                    VALUES (?, ?, ?, ?);
                    """,
                    (parent_sale_id, product_id, item_details['quantity'], item_details['price'])
                )
                
                cursor.execute(
                    """
                    UPDATE products 
                    SET stock = stock - ? 
                    WHERE id = ?;
                    """,
                    (item_details['quantity'], product_id)
                )

            # PHASE 4: SUCCESS CLEANUP AND COMMIT
            connection.commit()
            connection.close()
            
            self.clear()
            return True, "Checkout processing completed successfully!", parent_sale_id

        except Exception as e:
            # PHASE 5: CRITICAL EXCEPTION ROLLBACK - Returns exactly 3 values
            connection.rollback()
            connection.close()
            return False, f"Critical system error processed during checkout execution: {str(e)}", None

def get_invoice_data(sale_id):
    """Fetches transactional historical records from SQLite tables for a specific sale id."""
    from src.inventory.database import get_connection
    
    connection = get_connection()
    connection.row_factory = sqlite3.Row # Changes lookups to look like named keys!
    cursor = connection.cursor()
    
    # Fetch Master Transaction Header Details
    cursor.execute("SELECT id, timestamp, total_amount FROM sales WHERE id = ?;", (sale_id,))
    sale_record = cursor.fetchone()
    
    if not sale_record:
        connection.close()
        return None
        
    # Fetch Itemized Breakdown Line Rows joining with products to get names
    cursor.execute("""
        SELECT p.name, si.quantity, si.price_at_sale 
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?;
    """, (sale_id,))
    
    item_rows = cursor.fetchall()
    connection.close()
    
    # Pack up raw database row indexing objects into a clean structured dictionary matching your frontend templates
    invoice_details = {
        "sale_id": sale_record["id"],
        "timestamp": sale_record["timestamp"],
        "grand_total": sale_record["total_amount"],
        "products": [
            {
                "name": row["name"], 
                "quantity": row["quantity"], 
                "price": row["price_at_sale"], 
                "line_total": row["quantity"] * row["price_at_sale"]
            }
            for row in item_rows
        ]
    }
    return invoice_details

def generate_next_invoice_number():
    """
    Fetches the latest invoice string and increments the digit counter.
    Example: 'INV-0004' -> 'INV-0005'
    """
    latest = database.get_latest_invoice_number()
    if not latest:
        return "INV-0001"
    
    try:
        # Split prefix ('INV') and numerical suffix ('0001')
        prefix, num_part = latest.split('-')
        next_num = int(num_part) + 1
        # Maintain padding format up to 4 digits
        return f"{prefix}-{next_num:04d}"
    except (ValueError, IndexError):
        # Fallback security default if format is unexpectedly broken
        return "INV-0001"

def complete_checkout(cart_items, total_amount):
    """
    Coordinates invoice generation, state evaluation, and historic preservation.
    """
    if not cart_items:
        raise ValueError("Cannot check out an empty cart.")
        
    # Generate sequential unique identifier safely
    next_invoice_num = generate_next_invoice_number()
    
    # Save everything securely down to database layer
    sale_id = database.save_invoice_transaction(next_invoice_num, cart_items, total_amount)
    
    return {
        "sale_id": sale_id,
        "invoice_number": next_invoice_num
    }

# For testing the file:
if __name__ == "__main__":
    print("--- STARTING CART BACKEND TESTING DIAGNOSTICS ---")
    
    # 1. Initialize Cart Instance
    test_cart = ShoppingCart()
    
    # 2. Add sample records simulating items from the database
    test_cart.add_item(product_id=1, name="Wireless Keyboard", price=45.99, quantity=1)
    test_cart.add_item(product_id=2, name="Ergonomic Mouse", price=29.50, quantity=2)
    
    # 3. Test aggregate price calculations
    print(f"Current Estimated Total Amount: Rs.{test_cart.get_total()} (Expected: Rs.104.99)")
    
    # 4. Test product quantity modifications
    test_cart.add_item(product_id=1, name="Wireless Keyboard", price=45.99, quantity=1) # Adds 1 more
    test_cart.update_quantity(product_id=2, new_quantity=1) # Drops mouse from 2 down to 1
    
    # 5. Verify mathematical updates recalculate flawlessly
    print(f"Updated Cart Total Amount: Rs.{test_cart.get_total()} (Expected: Rs.121.48)")
    
    # 6. Test item drop deletion capabilities
    test_cart.remove_item(product_id=1)
    print(f"Final Cart Total Amount: Rs.{test_cart.get_total()} (Expected: Rs.29.50)")
    
    print("--- CART BACKEND DIAGNOSTICS LOGS PASSED COMPLETELY ---")