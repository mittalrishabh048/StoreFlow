from flask import Flask,render_template

# Create the application server instance object
app = Flask(__name__)

# Define the root home address route configuration
@app.route('/')
def dashboard():
    """Renders and serves the primary user inventory dashboard web page."""
    return render_template('dashboard.html')

if __name__ == "__main__":
    # Start the local development web server application
    app.run(debug=True)