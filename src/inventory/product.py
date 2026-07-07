class Product:
    def __init__(self, name: str,price: float,category:str,stock: int,id: int = None):
        # 1. Guard Clauses (Validate inputs before assignment)
        if not name.strip():
            raise ValueError("Product name cannot be empty.")
        if price < 0.0:
            raise ValueError("Product price cannot be negative.")
        if not category.strip():
            raise ValueError("Product category cannot be empty.")
        if stock < 0:
            raise ValueError("Product quantity cannot be negative.")
        
        # 2. Assignment (Only executes if validation passes)
        self.id=id
        self.name = name.strip()
        self.price = price
        self.category=category.strip()
        self.stock= stock

    def __str__(self):
        """Returns a string representation of the product for display purposes."""
        return f" {self.name:<20} | Rs.{self.price:<8.2f} | {self.category:<15} | {self.stock:<6}"