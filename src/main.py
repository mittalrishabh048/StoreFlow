import sys
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
        print("3. Update Entire Product Details")
        print("4. Stock In (Increase Stock)")
        print("5. Stock Out (Decrease Stock)")
        print("6. Search Products (By Name/Category)")
        print("7. View Low Stock Alerts")
        print("8. View Inventory Summary Report")
        print("9. Delete Product")
        print("10. Exit")
        
        choice = input("Enter your choice (1-10): ").strip()
        
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
            print("\n--- Update Product Details ---")
            name = input("Enter the product name to modify: ")
            

            try:
                new_price = float(input("Enter new product price: "))
                new_stock = int(input("Enter new total stock quantity: "))
            except ValueError:
                print("Error: Price must be a decimal and stock must be a whole number.")
                continue
            new_category = input("Enter new product category: ")

            
            try:
                success = manager.update_product(name, new_price, new_category, new_stock)
                if success:
                    print(f"Product '{name}' updated successfully.")
                else:
                    print(f"Error: No product found matching the name '{name}'.")
            except ValueError as e:
                print(f"Validation Error: {e}")
        
        elif choice == "4":
            print("\n--- Stock In Operations ---")
            name = input("Enter product name: ")
            try:
                qty = int(input("Enter shipment quantity to add: "))
                success = manager.stock_in(name, qty)
                if success:
                    print(f"Successfully added {qty} items to '{name}' stock levels.")
            except ValueError as e:
                print(f"Operation Error: {e}")

        elif choice == "5":
            print("\n--- Stock Out Operations ---")
            name = input("Enter product name: ")
            try:
                qty = int(input("Enter checkout quantity to deduct: "))
                success = manager.stock_out(name, qty)
                if success:
                    print(f"Successfully deducted {qty} items from '{name}' stock levels.")
            except ValueError as e:
                print(f"Operation Error: {e}")

        elif choice == "6":
            print("\n--- Partial Search Pipeline ---")
            keyword = input("Enter search keyword (matches name or category): ")
            results = manager.search_products(keyword)
            if not results:
                print(f"No match profiles found matching keyword: '{keyword}'")
            else:
                print(f"\nFound {len(results)} matches:")
                print(f"{'Product Name':<20} | {'Price':<9} | {'Category':<15} | {'Stock':<6}")
                print("-" * 60)
                for prod in results:
                    print(prod)

        elif choice == "7":
            print("\n--- Low Stock Alert Configuration ---")
            try:
                threshold = int(input("Enter low-stock threshold limit: "))
            except ValueError:
                print("Error: Threshold limit must be a whole number.")
                continue
            results = manager.get_low_stocks_alert(threshold)
            if not results:
                print(f"All products currently clear. No stock counts fall below {threshold}.")
            else:
                print(f"\n!!! ALERT: {len(results)} items falling below threshold !!!")
                for prod in results:
                    print(f"-> {prod.name} has only {prod.stock} units remaining.")

        elif choice == "8":
            print("\n--- Inventory Dashboard Statistics ---")
            summary = manager.get_inventory_summary()
            print(f"Total Unique Products Tracked : {summary['total_products']}")
            print(f"Total Portfolio Asset Value   : Rs.{summary['total_value']:.2f}")

        elif choice == "9":
            print("\n--- Delete Product From Storage ---")
            name = input("Enter the exact product name to remove permanently: ")
            success = manager.delete_product(name)
            if success:
                print(f"Product '{name}' was successfully removed from database records.")
            else:
                print(f"Error: No product found matching the name '{name}'.")
                
        elif choice == "10":
            print("\nClosing StoreFlow... Have a great day!")
            sys.exit()
        else:
            print("Invalid selection. Please enter a number between 1 and 10.")

if __name__ == "__main__":
    main()