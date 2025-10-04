from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import mysql.connector
import requests, os

app = Flask(__name__)

app.secret_key = os.urandom(24) 

DB_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',  
    'database': 'odoo'
}

#### Currency API
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


##DASHBOARD
@app.route('/')
def dashboard():
    """Renders the main dashboard/home page."""
    return render_template('dashboard.html')


##SIGNUUP
@app.route('/signup')
def signup():
    """Renders the admin signup page."""
    return render_template('signup.html')


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


##ADMINPANEL
@app.route('/admin_panel')
def admin_panel():
    return render_template('admin_dashboard.html')


@app.route('/user/delete', methods=['POST'])
def delete_user():
    """Deletes a user and flashes a confirmation message."""
    username = request.form.get('username')
    
    if not username:
        flash("Username is required to delete a user.", 'warning')
        return redirect(url_for('admin_panel'))

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        sql_delete_user = "DELETE FROM Users WHERE name = %s"
        cursor.execute(sql_delete_user, (username,))
        
        if cursor.rowcount == 0:
            
            flash(f"Error: No user found with the name '{username}'.", 'danger')
        else:
            
            flash(f"User '{username}' was successfully deleted.", 'success')
        
        cnx.commit()
        
    except mysql.connector.Error as err:
        if cnx:
            cnx.rollback()
        flash(f"Database Error: {err.msg}", 'danger')
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()

    
    return redirect(url_for('admin_panel'))



##MANAGER DASHBOARD
@app.route('/manager_dashboard')
def manager_dashboard():
    """Fetches and displays expenses awaiting approval for the manager's company."""
    if 'user_id' not in session or session.get('user_role') != 'Manager':
        return redirect(url_for('login'))

    pending_expenses = []
    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor(dictionary=True)

        company_id = session.get('company_id')

        
        query = """
            SELECT 
                e.expense_id,
                e.title,
                e.category,
                e.original_amount,
                e.original_currency,
                e.submission_date,
                u.name AS employee_name
            FROM Expense_Slips e
            JOIN Users u ON e.employee_id = u.id
            WHERE e.company_id = %s AND e.status = 'Submitted'
            ORDER BY e.submission_date ASC
        """
        cursor.execute(query, (company_id,))
        pending_expenses = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Database error fetching pending expenses: {err}")
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()

    return render_template('manager.html', 
                           pending_expenses=pending_expenses, 
                           user_name=session.get('user_name'))



@app.route('/update_expense_status', methods=['POST'])
def update_expense_status():
    """Handles the approval or rejection of an expense."""
    
    if 'user_id' not in session or session.get('user_role') != 'Manager':
        return redirect(url_for('login'))

    expense_id = request.form.get('expense_id')
    action = request.form.get('action') 

    if not expense_id or not action:
        
        return "Error: Missing form data.", 400

   
    new_status = 'Approved' if action == 'approve' else 'Rejected'

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        
        
        sql_update = "UPDATE Expense_Slips SET status = %s WHERE expense_id = %s"
        cursor.execute(sql_update, (new_status, expense_id))
        cnx.commit()

    except mysql.connector.Error as err:
        print(f"Database error updating expense status: {err}")
        
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()

    return redirect(url_for('manager_dashboard'))



##EMPLOYEEE DASHBOARD
@app.route('/employee_dashboard')
def employee_dashboard():
    """Fetches and displays expenses for the logged-in employee."""
    
    if 'user_id' not in session or session.get('user_role') != 'Employee':
        return redirect(url_for('login'))

    expenses = []
    db_connection = None
    cursor = None
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)
        
        employee_id = session.get('user_id')
        
        query = """
            SELECT title, description, date_incurred, category, original_amount, status 
            FROM Expense_Slips 
            WHERE employee_id = %s 
            ORDER BY date_incurred DESC
        """
        cursor.execute(query, (employee_id,))
        expenses = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Database error: {err}") 
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
            
    return render_template('u_dash.html', expenses=expenses, user_name=session.get('user_name'))


@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session or session.get('user_role') != 'Employee':
        return redirect(url_for('login'))

    description = request.form.get('expenseDescription')
    category = request.form.get('expenseCategory')
    date_incurred = request.form.get('expenseDate')
    amount = request.form.get('expenseAmount')


    employee_id = session.get('user_id')
    company_id = session.get('company_id')
    currency = session.get('currency')

    if not all([description, category, date_incurred, amount]):
        return "Error: All fields are required.", 400

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        
        sql_insert_expense = """
            INSERT INTO Expense_Slips 
            (employee_id, company_id, title, category, date_incurred, original_amount, original_currency, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        expense_data = (employee_id, company_id, description, category, date_incurred, amount, currency, 'Draft')
        
        cursor.execute(sql_insert_expense, expense_data)
        cnx.commit()

    except mysql.connector.Error as err:
        print(f"Database error on insert: {err}")
        return "Failed to save expense due to a database error.", 500
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()


    return redirect(url_for('employee_dashboard'))



##LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
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

          
            sql_select_user = """
                SELECT u.id, u.name, u.email, u.role, u.password, u.company_id, c.default_currency 
                FROM Users u 
                JOIN Companies c ON u.company_id = c.id 
                WHERE u.email = %s
            """
            cursor.execute(sql_select_user, (email,))
            user = cursor.fetchone()

            if user and password == user['password']:
                
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                session['company_id'] = user['company_id']       
                session['currency'] = user['default_currency']  

                if user['role'] == 'Employee':
                    return redirect(url_for('employee_dashboard'))
                elif user['role'] == 'Manager':
                    return redirect(url_for('manager_dashboard'))
                elif user['role'] == 'Admin':
                    return redirect(url_for('admin_panel'))
                else:
                    return "<h1>Login successful!</h1><p>Role not recognized.</p>"
            else:
                return redirect(url_for('login'))

        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return "A database error occurred.", 500
        finally:
            if cursor: cursor.close()
            if cnx: cnx.close()
                
    return render_template('login.html')



 
##LGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
          
if __name__ == '__main__':
    app.run(debug=True)
