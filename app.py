import os
import sys
from flask import Flask, render_template,request,redirect, url_for, flash,session

# Ensure the 'src' directory is in the Python search path to allow direct module imports
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

# FIXED: Import your actual InventoryManager class name
from src.inventory.manager import InventoryManager
from src.billing.billing import ShoppingCart,get_invoice_data

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
    """Gathers all analytical data frames and updates the administration portal."""
    from src.inventory import database
    
    # 1. Load active operational target KPIs
    kpi_data = database.get_dashboard_kpis()
    
    # 2. Poll inventory levels for low stock indicators (Alert threshold set to <= 5 units)
    low_stock_list = database.get_low_stock_alerts(threshold=5)
    
    # 3. Retrieve the top 5 highest velocity moving items
    top_products = database.get_top_selling_products(limit=5)
    
    # 4. Generate the rolling 7-day running revenue logs dataset
    weekly_trends = database.get_seven_day_revenue_summary()
    
    # 5. Pack everything neatly to send straight to the dashboard template engine
    return render_template(
        'dashboard.html',
        kpis=kpi_data,
        low_stock=low_stock_list,
        top_products=top_products,
        weekly_trends=weekly_trends
    )


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

@app.route('/cart')
def view_cart():
    """Reads the current session cookie state, hydrates a ShoppingCart engine object, and renders the dynamic UI."""
    # Read raw cookie dataset or default to clean empty structures
    session_cart_data = session.get('cart', {})
    
    # Instantiate the cart logic container and hydrate its dictionary state
    cart = ShoppingCart()
    cart.items = session_cart_data
    
    # Extract calculated collections for standard Jinja loops
    cart_items = cart.get_all_items()
    grand_total = cart.get_total()
    
    # Render the structured HTML view file, passing the dataset variables
    return render_template('cart.html', cart_items=cart_items, grand_total=grand_total)

@app.route('/cart/add/<product_name>', methods=['POST'])
def test_add_to_cart(product_name):
    """Fetches real item parameters and processes user-specified quantity choices via POST forms."""
    # 1. Look up the item from your database manager using the clean URL string parameter
    all_products = manager.get_all_products()
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be located in database records.", "error")
        return redirect(url_for('products_page'))
        
    # 2. Extract the user's custom quantity from the incoming form payload
    try:
        chosen_quantity = int(request.form.get('quantity', 1))
        if chosen_quantity <= 0:
            flash("Quantity must be a valid whole number greater than 0.", "error")
            return redirect(url_for('products_page'))
    except (ValueError, TypeError):
        flash("Invalid quantity count format submitted.", "error")
        return redirect(url_for('products_page'))
        
    # 3. Extract your current session cart dataset
    session_cart_data = session.get('cart', {})
    
    # 4. Instantiate and populate your ShoppingCart logic container
    cart = ShoppingCart()
    cart.items = session_cart_data
    
    # 5. Use the direct attributes. We pass target_product.name cleanly without extra prefixes!
    cart.add_item(
        product_id=str(target_product.id), 
        name=target_product.name, 
        price=target_product.price, 
        quantity=chosen_quantity
    )
    
    # 6. Save back to our encrypted cookie session wrapper
    session['cart'] = cart.items
    session.modified = True
    
    flash(f"Added {chosen_quantity}x '{target_product.name}' to your shopping cart!", "success")
    return redirect('/cart')

@app.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    """Evicts a specific product entry entirely from the session-backed shopping cart."""
    # 1. Fetch the raw session data dictionary state
    session_cart_data = session.get('cart', {})
    
    # 2. Hydrate our ShoppingCart engine class to leverage its built-in removal method
    cart = ShoppingCart()
    cart.items = session_cart_data
    
    # Ensure the identifier key parameter matches the format stored in our dictionary keys
    target_key = str(product_id)
    
    # 3. Drop the target row item out of memory
    if target_key in cart.items:
        cart.remove_item(target_key)
        flash("Item removed from your cart successfully.", "success")
    else:
        # Fallback safety check in case we are evicting an unindexed text string like "Product chips"
        # We search by checking if the product item ID or the dictionary key matches the incoming string
        matched_key = next((k for k, v in cart.items.items() if k == target_key or v.get('name') == product_id), None)
        if matched_key:
            cart.remove_item(matched_key)
            flash("Stale test record cleared from cart.", "success")
        else:
            flash("Target item could not be located in your active session.", "error")
            
    # 4. Serialize and save the clean collection layout back to the browser session cookie
    session['cart'] = cart.items
    session.modified = True
    
    # Return the user right back to their clean cart layout overview sheet
    return redirect('/cart')

@app.route('/cart/clear')
def test_clear_cart():
    """Temporary diagnostic route to simulate wiping out the active browser checkout session."""
    # Pop drops the 'cart' key out of our session dictionary completely
    session.pop('cart', None)
    flash("Session shopping cart data cleared completely.", "success")
    return redirect('/cart')

@app.route('/checkout', methods=['POST'])
def handle_checkout():
    from src.billing import billing
    from src.inventory import database
    
    # 1. Grab raw active cart data out of the live session wrapper
    session_cart_data = session.get('cart', {})
    if not session_cart_data:
        flash("Cannot process checkout: Your shopping cart is empty.", "error")
        return redirect(url_for('view_cart'))
        
    try:
        # 2. Re-compile the raw dictionary session data into structured items
        # Format required by database: (product_id, quantity, price, tax_placeholder)
        compiled_cart_items = []
        total_amount = 0.0
        
        for p_id, item_details in session_cart_data.items():
            qty = int(item_details['quantity'])
            price = float(item_details['price'])
            total_amount += qty * price
            # Append as tuple matching expected unpacked iteration loop variables
            compiled_cart_items.append((int(p_id), qty, price, 0.00))
            
        # 3. Process the master transaction engine and obtain tracking details
        invoice_meta = billing.complete_checkout(compiled_cart_items, round(total_amount, 2))
        
        # 4. CRITICAL SYNC STEP: Retrieve the live saved database snapshot rows!
        # We reuse your excellent get_invoice_data method from billing.py
        real_invoice_data = billing.get_invoice_data(invoice_meta["sale_id"])
        
        # 5. Inject the missing sequential invoice format field into the dictionary payload
        real_invoice_data["invoice_number"] = invoice_meta["invoice_number"]
        
        # 6. Flash confirmation message and purge session cart storage
        session.pop('cart', None)
        flash("Transaction successfully completed!", "success")
        
        # 7. Render your template using the exact keys it needs
        return render_template("invoice.html", invoice=real_invoice_data)
        
    except Exception as e:
        flash(f"Checkout Transaction Failed: {str(e)}", "error")
        return redirect(url_for('view_cart'))

@app.route('/sales')
def sales_history():
    """Fetches all previous historical orders and passes them to the index list view."""
    from src.inventory import database

    # Capture inputs from URL parameters safely using request.args
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    product_name = request.args.get('product_name', '').strip()
    
    # Pass arguments straight to dynamic query architecture
    past_invoices = database.get_all_invoices(
        date_from=date_from or None,
        date_to=date_to or None,
        product_name=product_name or None
    )

    # Preserve filter states back into template so the form fields remain populated
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "product_name": product_name
    }
    
    return render_template('sales_history.html', invoices=past_invoices, filters=filters)


@app.route('/invoice/<int:sale_id>')
def view_invoice(sale_id):
    """Renders a historical receipt summary view for a verified sale transaction record."""
    from src.billing import billing
    
    # Call your data utility layer to fetch the snapshot metadata 
    invoice = billing.get_invoice_data(sale_id)
    
    # Handle invalid invoice IDs gracefully
    if not invoice:
        flash(f"Invoice reference ID #{sale_id} could not be located in historical archives.", "error")
        return redirect(url_for('sales_history'))
        
    return render_template('invoice.html', invoice=invoice)

# Implement the dedicated void route handler
@app.route('/void_sale/<int:sale_id>', methods=['POST'])
def handle_void_sale(sale_id):
    """Processes transactional cancellations and restores inventory."""
    from src.billing import billing
    
    success, message = billing.void_sale(sale_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for('sales_history'))

if __name__ == "__main__":
    app.run(debug=True)