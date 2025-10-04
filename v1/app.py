from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Simple in-memory storage (replace with DB for production)
db = {
    "company": None,
    "admin_user": None,
    "users": []
}

# Country to currency mapping
COUNTRY_CURRENCY = {
    "India": {"currency": "INR", "locale": "en_IN"},
    "United States": {"currency": "USD", "locale": "en_US"},
    "United Kingdom": {"currency": "GBP", "locale": "en_GB"},
    "Germany": {"currency": "EUR", "locale": "de_DE"},
}

@app.route("/", methods=["GET", "POST"])
def setup():
    if db["company"]:
        # Show company and admin info
        return render_template("dashboard.html", company=db["company"], admin=db["admin_user"])
    if request.method == "POST":
        country = request.form["country"]
        company_name = request.form["company_name"]
        admin_name = request.form["admin_name"]

        currency = COUNTRY_CURRENCY[country]["currency"]
        db["company"] = {"name": company_name, "country": country, "currency": currency}
        db["admin_user"] = {"name": admin_name, "role": "Admin"}
        return redirect("/")
    return render_template("setup.html", countries=COUNTRY_CURRENCY)

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    # For demo, just store user info in memory (avoid plaintext password in real apps)
    db["users"].append({"username": username, "email": email, "password": password})
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
