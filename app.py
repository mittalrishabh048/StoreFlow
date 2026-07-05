import os
import sys
from flask import Flask, render_template

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


if __name__ == "__main__":
    app.run(debug=True)