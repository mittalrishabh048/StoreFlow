from src.inventory.product import Product

class InventoryManager:
    def __init__(self):
        # The temporary, in-memory collection holding Product objects
        self.products = []

    def add_product(self, name: str, sku: str, price: float, quantity: int) -> Product:
        """Instantiates a product cleanly and appends it to the collection."""
        # Check if the SKU already exists to maintain uniqueness
        for prod in self.products:
            if prod.sku == sku.strip().upper():
                raise ValueError(f"A product with SKU '{sku}' already exists.")
        
        # Create and save the new product instance
        new_product = Product(name, sku, price, quantity)
        self.products.append(new_product)
        return new_product

    def get_all_products(self):
        """Returns the raw list of all active products."""
        return self.products

    def delete_product_by_sku(self, sku: str) -> bool:
        """Searches for a product by its unique SKU and removes it safely."""
        target_sku = sku.strip().upper()
        for prod in self.products:
            if prod.sku == target_sku:
                self.products.remove(prod)
                return True # Deletion successful
        return False # Product not found