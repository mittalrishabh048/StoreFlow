class Product:
    def __init__(self, name: str, sku: str, price: float, quantity: int):
        # 1. Guard Clauses (Validate inputs before assignment)
        if not name.strip():
            raise ValueError("Product name cannot be empty.")
        if not sku.strip():
            raise ValueError("SKU cannot be empty.")
        if price < 0.0:
            raise ValueError("Product price cannot be negative.")
        if quantity < 0:
            raise ValueError("Product quantity cannot be negative.")
        
        # 2. Assignment (Only executes if validation passes)
        self.name = name.strip()
        self.sku = sku.strip().upper()
        self.price = price
        self.quantity = quantity

    def __str__(self):
        """Returns a string representation of the product for display purposes."""
        return f"{self.sku:<10} | {self.name:<20} | ${self.price:<8.2f} | {self.quantity:<6}"