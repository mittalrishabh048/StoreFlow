import os
import sys
from flask import Flask, render_template,request,redirect, url_for, flash

# Ensure the 'src' directory is in the Python search path to allow direct module imports
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

# FIXED: Import your actual InventoryManager class name
from src.inventory.manager import InventoryManager

# Instantiate the engine constructor
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

app.secret_key = 'storeflow_secure_session_encryption_bypass_key'

# FIXED: Initialize without passing db_path, since your __init__ handles it internally
manager = InventoryManager()


@app.route('/')
def dashboard():
    """Serves the primary system management user portal interface."""
    return render_template('dashboard.html')


@app.route('/products')
def products_page():
    """Fetches records through the manager layer and serves the read-only list view."""
    # Retrieve product array data using your manager instance
    all_products = manager.get_all_products()
    return render_template('products.html', products=all_products)

@app.route('/add-product', methods=['GET', 'POST'])
def add_product_page():
    """Handles form presentation, server-side data validation, and value preservation."""
    errors = []
    
    # Track submitted values to preserve them in the form if validation fails
    form_data = {
        'name': '',
        'price': '',
        'category': '',
        'quantity': ''
    }
    
    if request.method == 'POST':
        # Retrieve values and trim trailing whitespace strings
        form_data['name'] = request.form.get('name', '').strip()
        form_data['price'] = request.form.get('price', '').strip()
        form_data['category'] = request.form.get('category', '').strip()
        form_data['quantity'] = request.form.get('quantity', '').strip()
        
        # 1. Product Name Validation Check
        if not form_data['name']:
            errors.append("Product name cannot be empty or consist only of spaces.")
            
        # 2. Category Validation Check
        if not form_data['category']:
            errors.append("Category field cannot be left blank.")
            
        # 3. Numeric Price Validation Check
        try:
            price_val = float(form_data['price'])
            if price_val < 0:
                errors.append("Unit price cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Unit price must be a valid numeric decimal number.")
            
        # 4. Numeric Quantity Validation Check
        try:
            qty_val = int(form_data['quantity'])
            if qty_val < 0:
                errors.append("Quantity in stock cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Quantity count must be a valid whole number integer.")

        # Step 4: Core Persistence and Redirect Engine Operation
        if not errors:
            # Save the clean data record directly through your backend system logic
            # (Adjust parameters here if your add_product takes positional args instead)
            manager.add_product(
                name=form_data['name'],
                price=price_val,
                category=form_data['category'],
                stock=qty_val
            )
            
            # Queue up a success notification token for the flash payload
            flash(f"Success! '{form_data['name']}' has been added to the inventory.", "success")
            
            # PRG Pattern: Instantly break out of POST by redirecting to the GET route
            return redirect(url_for('products_page'))
    
    # If errors exist or it's a GET request, load form with errors and data state
    return render_template('addproduct.html', errors=errors, form_data=form_data)

@app.route('/edit-product/<product_name>', methods=['GET', 'POST'])
def edit_product_page(product_name):
    """Loads existing record specifications (GET) and processes update validation and persistence (POST)."""
    errors = []
    
    # 1. Fetch the existing product record through your manager to populate the form
    all_products = manager.get_all_products()
    # Find the specific product object matching the URL parameter name
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be located.", "error")
        return redirect(url_for('products_page'))
        
    # Setup initial form data mapping using the current database attributes
    form_data = {
        'name': target_product.name,
        'price': str(target_product.price),
        'category': getattr(target_product, 'category', ''), # Uses fallback if category isn't a direct attribute
        'quantity': str(target_product.stock)
    }
    
    if request.method == 'POST':
        # Grab updated user inputs
        form_data['price'] = request.form.get('price', '').strip()
        form_data['category'] = request.form.get('category', '').strip()
        form_data['quantity'] = request.form.get('quantity', '').strip()
        
        # Server-side Validation Checks (same as step 3)
        if not form_data['category']:
            errors.append("Category field cannot be left blank.")
        try:
            price_val = float(form_data['price'])
            if price_val < 0:
                errors.append("Unit price cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Unit price must be a valid numeric number.")
        try:
            qty_val = int(form_data['quantity'])
            if qty_val < 0:
                errors.append("Quantity in stock cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Quantity count must be a valid whole number.")

        # Save Updates if validation passes
        if not errors:
            # Call your manager update function (adjust naming conventions if yours differs, e.g., update_product)
            # Depending on your backend design, we pass the identifier name and the updated parameters
            manager.update_product(
                name=product_name,
                new_price=price_val,
                new_category=form_data['category'],
                new_stock=qty_val
            )
            
            flash(f"Success! '{product_name}' updates have been saved.", "success")
            return redirect(url_for('products_page'))
            
    # We reuse our clean form UI file template structure for the edit view screen
    return render_template('addproduct.html', errors=errors, form_data=form_data, is_edit=True, product_name=product_name)

@app.route('/delete-product/<product_name>', methods=['GET', 'POST'])
def delete_product_page(product_name):
    """Presents a safety confirmation screen (GET) and processes record removal (POST)."""
    
    # Verify the product actually exists before trying to manage it
    all_products = manager.get_all_products()
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be found.", "error")
        return redirect(url_for('products_page'))

    if request.method == 'POST':
        # Call your manager delete function (adjust naming convention if your function differs, e.g., remove_product)
        manager.delete_product(name=product_name)
        
        # Queue up a dynamic feedback confirmation alert
        flash(f"Success! '{product_name}' has been permanently removed from inventory.", "success")
        
        # PRG Pattern: Redirect back to the read list view
        return redirect(url_for('products_page'))

    # GET request: Render the safety confirmation layout view
    return render_template('delete_confirm.html', product_name=product_name)

if __name__ == "__main__":
    app.run(debug=True)