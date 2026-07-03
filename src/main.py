from src.inventory.database import init_db
from src.inventory.manager import InventoryManager

def main():
    # 1. Initialize database file and table layout on application startup
    init_db()
    
    # 2. Instantiate our backend pipeline controller
    manager = InventoryManager()

    print("=== Welcome to StoreFlow ===")
    
    while True:
        print("\n--- Main Menu ---")
        print("1. Add Product")
        print("2. Display All Products")
        print("3. Update Product Stock")
        print("4. Delete Product")
        print("5. Exit")
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == "1":
            print("\n--- Add New Product ---")
            name = input("Enter product name: ")
            
            # Catching conversion issues for numeric types right at the boundary
            try:
                price = float(input("Enter product price: "))
                stock = int(input("Enter initial stock quantity: "))
            except ValueError:
                print("Error: Price must be a decimal number and stock must be a whole number.")
                continue
                
            category = input("Enter product category: ")
            
            # Send data fields to our backend controller manager layer
            try:
                new_prod = manager.add_product(name, price, category, stock)
                print(f"\nSuccess! Added: {new_prod.name} into storage system.")
            except ValueError as e:
                # Catches both our custom guard clause violations and duplicate names
                print(f"Validation Error: {e}")
                
        elif choice == "2":
            print("\n--- Current Inventory Status ---")
            products = manager.get_all_products()
            
            if not products:
                print("Inventory is completely empty.")
            else:
                # Print clean, scannable column headers
                print(f"{'Product Name':<20} | {'Price':<9} | {'Category':<15} | {'Stock':<6}")
                print("-" * 60)
                for prod in products:
                    print(prod) # Leverages the __str__ method inside your Product class
                    
        elif choice == "3":
            print("\n--- Update Stock Level ---")
            name = input("Enter the product name to modify: ")
            try:
                new_stock = int(input("Enter new total stock quantity: "))
                success = manager.update_product_stock(name, new_stock)
                if success:
                    print(f"Stock levels for '{name}' updated successfully.")
                else:
                    print(f"Error: No product found matching the name '{name}'.")
            except ValueError as e:
                print(f"Error: {e}")
                
        elif choice == "4":
            print("\n--- Delete Product From Storage ---")
            name = input("Enter the exact product name to remove permanently: ")
            
            success = manager.delete_product_by_name(name)
            if success:
                print(f"Product '{name}' was successfully removed from database records.")
            else:
                print(f"Error: No product found matching the name '{name}'.")
                
        elif choice == "5":
            print("\nClosing StoreFlow... Have a great day!")
            break
        else:
            print("Invalid selection. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main()