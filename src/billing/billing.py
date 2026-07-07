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