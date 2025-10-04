from flask import Flask, request, jsonify, render_template, redirect, url_for
import mysql.connector
import requests

app = Flask(__name__)

DB_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',  
    'database': 'odoo'
}

def get_currency_from_country(country_name):
    """Fetches the currency code for a given country name."""
    try:
        response = requests.get(f"https://restcountries.com/v3.1/name/{country_name}?fullText=true")
        response.raise_for_status()  
        country_data = response.json()[0]
        currency_code = list(country_data['currencies'].keys())[0]
        return currency_code
    except Exception as e:
        print(f"Could not fetch currency for '{country_name}': {e}")
        return "USD"  


@app.route('/')
def dashboard():
    """Renders the main dashboard/home page."""
    return render_template('dashboard.html')

@app.route('/signup')
def signup():
    """Renders the admin signup page."""
    return render_template('signup.html')

@app.route('/admin_panel')
def admin_panel():
    return "<h1>Welcome, Admin!</h1><p>This is your control panel.</p>"

@app.route('/manager_dashboard')
def manager_dashboard():
    return "<h1>Welcome, Manager!</h1><p>This is your control panel.</p>"

@app.route('/employee_dashboard')
def employee_dashboard():
    return "<h1>Welcome, Employee   !</h1><p>This is your control panel.</p>"


@app.route('/signup/admin', methods=['POST'])
def admin_signup():
    """Handles the admin signup form submission and creates company/user."""
    admin_name = request.form.get('adminName')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirmPassword')
    company_name = request.form.get('companyName')
    country = request.form.get('country')

    form_fields = {
        "Admin Name": admin_name,
        "Email": email,
        "Password": password,
        "Confirm Password": confirm_password,
        "Company Name": company_name,
        "Country": country
    }

    for field_name, value in form_fields.items():
        if not value:
            return f"Error: The '{field_name}' field is required and cannot be empty.", 400

    if password != confirm_password:
        return "Error: Passwords do not match!", 400

    default_currency = get_currency_from_country(country)

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cnx.start_transaction()

        sql_insert_company = "INSERT INTO Companies (name, country, default_currency) VALUES (%s, %s, %s)"
        company_data = (company_name, country, default_currency)
        cursor.execute(sql_insert_company, company_data)
        new_company_id = cursor.lastrowid

        sql_insert_user = "INSERT INTO Users (company_id, name, email, password, role) VALUES (%s, %s, %s, %s, %s)"
        user_data = (new_company_id, admin_name, email, password, 'Admin')
        cursor.execute(sql_insert_user, user_data)

        cnx.commit()
        
        return redirect(url_for('login'))

    except mysql.connector.Error as err:
        if cnx:
            cnx.rollback()
            
        print(f"Database error: {err}")
        error_message = f"Database Error: {err.msg}"
        return error_message, 500
        
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles both rendering the login page (GET) and processing the login form (POST)."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return "Email and password are required", 400
        
        cnx = None
        cursor = None
        try:
            cnx = mysql.connector.connect(**DB_CONFIG)
            cursor = cnx.cursor(dictionary=True)

            sql_select_user = "SELECT id, name, email, role, password FROM Users WHERE email = %s"
            cursor.execute(sql_select_user, (email,))
            user = cursor.fetchone()

            if user and password == user['password']:
                if user['role'] == 'Admin':
                    return redirect(url_for('admin_panel'))
                elif user['role'] == 'Manager':
                    return redirect(url_for('manager_dashboard'))
                elif user['role'] == 'Employee':
                    return redirect(url_for('employee_dashboard'))
                else:
                    return "<h1>Login successful!</h1><p>Role not recognized.</p>"
            else:
                return "Invalid email or password", 401

        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return "A database error occurred.", 500
        finally:
            if cursor:
                cursor.close()
            if cnx:
                cnx.close()
                
    print("Serving the login.html page...")
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)

