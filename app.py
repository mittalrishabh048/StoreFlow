import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response

# Ensure the 'src' directory is in the Python search path to allow direct module imports
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, 'src'))

# FIXED: Import your actual InventoryManager class name
from src.inventory.manager import InventoryManager
from src.billing.billing import ShoppingCart, get_invoice_data

# Instantiate the engine constructor
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

app.secret_key = 'storeflow_secure_session_encryption_bypass_key'

# FIXED: Initialize without passing db_path, since your __init__ handles it internally
manager = InventoryManager()

@app.before_request
def lock_protected_routes():
    """Global route guard checking session variables before serving protected views."""
    # List of public endpoints that anyone can access without being logged in
    public_endpoints = ['login_route', 'static']
    
    # If the user is trying to access a protected page and is NOT logged in, redirect them
    if request.endpoint not in public_endpoints and not session.get('logged_in'):
        flash("Unauthorized access. Please log in first.", "error")
        return redirect(url_for('login_route'))

@app.context_processor
def inject_global_settings():
    """Automatically injects the live database settings into every single HTML template."""
    try:
        current_configs = manager.get_system_settings()
        return dict(settings=current_configs)
    except Exception as e:
        # Secure fallback block to prevent app crashes if the database table isn't fully ready
        print(f"[CONTEXT PROCESSOR ERROR] Fallback applied. Reason: {e}")
        return dict(settings={
            "store_name": "StoreFlow Retail",
            "address": "",
            "phone": "",
            "email": "",
            "currency": "Rs.",
            "tax_rate": 0.0,
            "low_stock_threshold": 5
        })

@app.route('/')
def dashboard():
    """Gathers all analytical data frames and updates the administration portal."""
    from src.inventory import database
    
    # 1. Fetch current live system configuration options using your global instance
    current_settings = manager.get_system_settings()
    alert_limit = current_settings["low_stock_threshold"]
    
    # 2. Extract today's revenue, sales count, and volume indicators
    today_revenue = manager.get_todays_revenue()
    today_sales_count = manager.get_todays_sales_count()
    today_units_sold = manager.get_todays_units_sold()
    
    # 3. Pull metrics from database
    kpi_data = database.get_dashboard_kpis()
    
    # 4. Use your global instance to pull the Product object list
    low_stock_list = manager.get_low_stocks_alert(threshold=alert_limit)
    
    top_products = database.get_top_selling_products(limit=5)
    weekly_trends = database.get_seven_day_revenue_summary()

    # 5. Pack everything neatly to send straight to the dashboard template engine
    return render_template(
        'dashboard.html',
        revenue=today_revenue,
        sales_count=today_sales_count,
        units_sold=today_units_sold,
        kpis=kpi_data,
        low_stock_items=low_stock_list,  # Matches template loop variable name
        top_products=top_products,
        weekly_trends=weekly_trends
    )


@app.route('/products')
def products_page():
    """Fetches records through the manager layer and serves the read-only list view."""
    all_products = manager.get_all_products()
    return render_template('products.html', products=all_products)

@app.route('/add-product', methods=['GET', 'POST'])
def add_product_page():
    """Handles form presentation, server-side data validation, and value preservation."""
    errors = []
    
    form_data = {
        'name': '',
        'price': '',
        'category': '',
        'quantity': ''
    }
    
    if request.method == 'POST':
        # Step 10: Input Sanitization - Trim extra wrapping whitespace spaces
        form_data['name'] = request.form.get('name', '').strip()
        form_data['price'] = request.form.get('price', '').strip()
        form_data['category'] = request.form.get('category', '').strip()
        form_data['quantity'] = request.form.get('quantity', '').strip()
        
        # Step 8 & 9: Server-side Validation Auditing (Empty field assertions)
        if not form_data['name']:
            errors.append("Product name cannot be empty or consist only of spaces.")
            
        if not form_data['category']:
            errors.append("Category field cannot be left blank.")
            
        # Numeric parsing and invalid range evaluation
        try:
            price_val = float(form_data['price'])
            if price_val < 0:
                errors.append("Unit price cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Unit price must be a valid numeric decimal number.")
            
        try:
            qty_val = int(form_data['quantity'])
            if qty_val < 0:
                errors.append("Quantity in stock cannot be a negative value.")
        except (ValueError, TypeError):
            errors.append("Quantity count must be a valid whole number integer.")

        if not errors:
            manager.add_product(
                name=form_data['name'],
                price=price_val,
                category=form_data['category'],
                stock=qty_val
            )
            
            flash(f"Success! '{form_data['name']}' has been added to the inventory.", "success")
            return redirect(url_for('products_page'))
        else:
            # Transfer arrays over to the standardized centralized base flash template block
            for err in errors:
                flash(err, "error")
    
    return render_template('addproduct.html', errors=errors, form_data=form_data)

@app.route('/edit-product/<product_name>', methods=['GET', 'POST'])
def edit_product_page(product_name):
    """Loads existing record specifications (GET) and processes update validation and persistence (POST)."""
    errors = []
    
    all_products = manager.get_all_products()
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be located.", "error")
        return redirect(url_for('products_page'))
        
    form_data = {
        'name': target_product.name,
        'price': str(target_product.price),
        'category': getattr(target_product, 'category', ''), 
        'quantity': str(target_product.stock)
    }
    
    if request.method == 'POST':
        # Step 10: Clean input data whitespace
        form_data['price'] = request.form.get('price', '').strip()
        form_data['category'] = request.form.get('category', '').strip()
        form_data['quantity'] = request.form.get('quantity', '').strip()
        
        # Step 8 & 9: Server-side data state constraints validation checking
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

        if not errors:
            manager.update_product(
                name=product_name,
                new_price=price_val,
                new_category=form_data['category'],
                new_stock=qty_val
            )
            
            flash(f"Success! '{product_name}' updates have been saved.", "success")
            return redirect(url_for('products_page'))
        else:
            # Transfer message strings out to main application flash rendering registry logic loops
            for err in errors:
                flash(err, "error")
            
    return render_template('addproduct.html', errors=errors, form_data=form_data, is_edit=True, product_name=product_name)

@app.route('/delete-product/<product_name>', methods=['GET', 'POST'])
def delete_product_page(product_name):
    """Presents a safety confirmation screen (GET) and processes record removal (POST)."""
    all_products = manager.get_all_products()
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be found.", "error")
        return redirect(url_for('products_page'))

    if request.method == 'POST':
        manager.delete_product(name=product_name)
        flash(f"Success! '{product_name}' has been permanently removed from inventory.", "success")
        return redirect(url_for('products_page'))

    return render_template('delete_confirm.html', product_name=product_name)

@app.route('/cart')
def view_cart():
    """Compiles the transactional active cart elements and sums overall costs."""
    if not session.get('logged_in'):
        return redirect(url_for('login_route'))
        
    current_cart = session.get('cart', {})
    calculated_grand_total = 0.0
    for key, item in current_cart.items():
        try:
            price = float(item.get('price', 0.0))
            qty = int(item.get('quantity', 0))
            calculated_grand_total += price * qty
        except (ValueError, TypeError):
            continue

    return render_template(
        'cart.html', 
        cart_items=current_cart, 
        cart_total=calculated_grand_total
    )

@app.route('/cart/add/<product_name>', methods=['POST'])
def test_add_to_cart(product_name):
    """Fetches real item parameters and processes user-specified quantity choices via POST forms."""
    all_products = manager.get_all_products()
    target_product = next((p for p in all_products if p.name == product_name), None)
    
    if not target_product:
        flash(f"Error: Product '{product_name}' could not be located in database records.", "error")
        return redirect(url_for('products_page'))
        
    try:
        chosen_quantity = int(request.form.get('quantity', 1))
        if chosen_quantity <= 0:
            flash("Quantity must be a valid whole number greater than 0.", "error")
            return redirect(url_for('products_page'))
    except (ValueError, TypeError):
        flash("Invalid quantity count format submitted.", "error")
        return redirect(url_for('products_page'))
        
    session_cart_data = session.get('cart', {})
    cart = ShoppingCart()
    cart.items = session_cart_data
    
    cart.add_item(
        product_id=str(target_product.id), 
        name=target_product.name, 
        price=target_product.price, 
        quantity=chosen_quantity
    )
    
    session['cart'] = cart.items
    session.modified = True
    
    flash(f"Added {chosen_quantity}x '{target_product.name}' to your shopping cart!", "success")
    return redirect('/cart')

@app.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    """Evicts a specific product entry entirely from the session-backed shopping cart."""
    session_cart_data = session.get('cart', {})
    cart = ShoppingCart()
    cart.items = session_cart_data
    target_key = str(product_id)
    
    if target_key in cart.items:
        cart.remove_item(target_key)
        flash("Item removed from your cart successfully.", "success")
    else:
        matched_key = next((k for k, v in cart.items.items() if k == target_key or v.get('name') == product_id), None)
        if matched_key:
            cart.remove_item(matched_key)
            flash("Stale test record cleared from cart.", "success")
        else:
            flash("Target item could not be located in your active session.", "error")
            
    session['cart'] = cart.items
    session.modified = True
    return redirect('/cart')

@app.route('/cart/clear')
def test_clear_cart():
    """Wipes out the active browser checkout session variables."""
    session.pop('cart', None)
    flash("Session shopping cart data cleared completely.", "success")
    return redirect('/cart')

@app.route('/checkout', methods=['POST'])
def handle_checkout():
    from src.billing import billing
    
    session_cart_data = session.get('cart', {})
    if not session_cart_data:
        flash("Cannot process checkout: Your shopping cart is empty.", "error")
        return redirect(url_for('view_cart'))
        
    try:
        current_settings = manager.get_system_settings()
        active_tax_rate = current_settings["tax_rate"] 

        compiled_cart_items = []
        base_subtotal = 0.0
        
        for p_id, item_details in session_cart_data.items():
            qty = int(item_details['quantity'])
            price = float(item_details['price'])
            base_subtotal += qty * price
            
            item_tax = price * active_tax_rate
            compiled_cart_items.append((int(p_id), qty, price, round(item_tax, 2)))
            
        total_tax_calculated = base_subtotal * active_tax_rate
        final_grand_total = base_subtotal + total_tax_calculated

        invoice_meta = billing.complete_checkout(compiled_cart_items, round(final_grand_total, 2))
        real_invoice_data = billing.get_invoice_data(invoice_meta["sale_id"])
        real_invoice_data["invoice_number"] = invoice_meta["invoice_number"]
        
        session.pop('cart', None)
        flash("Transaction successfully completed!", "success")
        return render_template("invoice.html", invoice=real_invoice_data)
        
    except Exception as e:
        flash(f"Checkout Transaction Failed: {str(e)}", "error")
        return redirect(url_for('view_cart'))

@app.route('/sales')
def sales_history():
    """Fetches all previous historical orders and passes them to the index list view."""
    from src.inventory import database

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    product_name = request.args.get('product_name', '').strip()
    
    past_invoices = database.get_all_invoices(
        date_from=date_from or None,
        date_to=date_to or None,
        product_name=product_name or None
    )

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
    
    invoice = billing.get_invoice_data(sale_id)
    if not invoice:
        flash(f"Invoice reference ID #{sale_id} could not be located in historical archives.", "error")
        return redirect(url_for('sales_history'))
        
    return render_template('invoice.html', invoice=invoice)

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

@app.route('/report/inventory')
def inventory_report_page():
    """Renders current stock status levels and capital asset valuations."""
    report_data = manager.generate_inventory_report()
    return render_template('inventory_report.html', report=report_data)

@app.route('/report/sales')
def sales_report_page():
    """Processes dynamic transaction summaries with active query string boundaries."""
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    report_data = manager.generate_sales_report(
        start_date=start_date or None,
        end_date=end_date or None
    )
    
    filters = {"start_date": start_date, "end_date": end_date}
    return render_template('sales_report.html', report=report_data, filters=filters)

@app.route('/report/inventory/csv')
def export_inventory_csv():
    """Generates and drops a standard structural inventory evaluation spreadsheet."""
    csv_data = manager.generate_inventory_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_report.csv"}
    )

@app.route('/report/sales/csv')
def export_sales_csv():
    """Generates and matches sales metrics with custom range boundary filenames."""
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    csv_data = manager.generate_sales_csv(
        start_date=start_date or None,
        end_date=end_date or None
    )
    
    if start_date and end_date:
        filename = f"sales_{start_date}_to_{end_date}.csv"
    elif start_date:
        filename = f"sales_from_{start_date}.csv"
    elif end_date:
        filename = f"sales_until_{end_date}.csv"
    else:
        filename = "sales_report_all.csv"
        
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    """Handles template presentation and session validation for system access authentication."""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        success, message = manager.authenticate_user(username, password)
        if success:
            session['logged_in'] = True
            session['username'] = username.strip()
            flash("Welcome back! System access verification approved.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash(message, "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout_route():
    """Clears the active user session and redirects back to the login screen."""
    session.clear()
    flash("You have been signed out successfully.", "success")
    return redirect(url_for('login_route'))

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """Manages system customization parameters and configuration metrics update pipelines."""
    if not session.get('logged_in'):
        flash("Access denied. Please log in first.", "error")
        return redirect(url_for('login_route'))
        
    if request.method == 'POST':
        # Step 10: Input Sanitization - Clean trailing empty spaces across layout text values
        store_name = request.form.get("store_name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        currency = request.form.get("currency", "").strip()
        raw_tax = request.form.get("tax_rate", "").strip()
        raw_threshold = request.form.get("low_stock_threshold", "").strip()
        
        # Step 8 & 9: Server-side validation framework checking against blanks
        if not store_name or not currency or not raw_tax or not raw_threshold:
            flash("Configuration Error: Required inputs cannot be left blank.", "error")
            current_configs = manager.get_system_settings()
            return render_template('settings.html', settings=current_configs)
            
        try:
            tax_rate = float(raw_tax)
            threshold = int(raw_threshold)
            
            # Bound validation matching logic limits rules (Step 8)
            if tax_rate < 0.0 or tax_rate > 1.0:
                flash("Configuration Error: Tax rate coefficient must fall between 0.00 and 1.00.", "error")
                current_configs = manager.get_system_settings()
                return render_template('settings.html', settings=current_configs)
                
            if threshold < 0:
                flash("Configuration Error: Low Stock alert limit values cannot be negative.", "error")
                current_configs = manager.get_system_settings()
                return render_template('settings.html', settings=current_configs)
                
            # If validated, pass formatted properties matrix to storage layers cleanly
            form_payload = {
                "store_name": store_name,
                "address": address,
                "phone": phone,
                "email": email,
                "currency": currency,
                "tax_rate": tax_rate,
                "low_stock_threshold": threshold
            }
            
            success, message = manager.update_system_settings(form_payload)
            if success:
                flash(message, "success")
                return redirect(url_for('settings_page'))
            else:
                flash(message, "error")
                
        except (ValueError, TypeError):
            flash("Configuration Error: Tax rate must be a float decimal, and alert levels must be an integer.", "error")
            
    current_configs = manager.get_system_settings()
    return render_template('settings.html', settings=current_configs)

@app.errorhandler(404)
def page_not_found(e):
    """Renders the custom 404 error template frame interface."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Renders the custom 500 error template frame interface."""
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)