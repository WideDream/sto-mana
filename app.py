from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "store_secret_key_2025"

# ---------- JINJA2 FILTERS ----------

@app.template_filter('rwf')
def format_rwf(value):
    """Format number as Rwandan Francs with thousand separators."""
    try:
        return f"RWF {int(value):,.0f}"
    except (ValueError, TypeError):
        return "RWF 0"

# ---------- HELPERS ----------

def safe_float(value, default=0.0):
    """Safely convert value to float, return default if invalid."""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default

# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    return conn

def migrate_records_add_customer_id(conn):
    """Safely migrate existing DB to add missing columns."""
    cur = conn.execute("PRAGMA table_info(records)")
    cols = {r["name"] for r in cur.fetchall()}
    
    # Add missing columns one by one
    if "customer_id" not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN customer_id INTEGER")
    if "due_date" not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN due_date TEXT")
    if "payment_status" not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN payment_status TEXT DEFAULT 'pending'")
    if "notes" not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN notes TEXT")
    
    conn.commit()

def init_db():
    conn = get_db()

    # Users table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Customers table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT UNIQUE,
        phone TEXT,
        address TEXT,
        note TEXT,
        credit_limit REAL DEFAULT 0,
        created_at TEXT
    )
    """)

    # Products table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        unit TEXT,
        price REAL,
        stock REAL,
        created_at TEXT
    )
    """)

    # Records table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        product TEXT,
        quantity REAL,
        unit_price REAL,
        total REAL,
        paid REAL,
        loan REAL,
        date TEXT,
        due_date TEXT,
        payment_status TEXT DEFAULT 'pending',
        notes TEXT
    )
    """)

    # Default admin user
    user = conn.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if not user:
        conn.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            ("admin", generate_password_hash("admin123"))
        )

    conn.commit()
    
    # Ensure existing DBs have customer_id column
    try:
        migrate_records_add_customer_id(conn)
    except Exception:
        pass
    
    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            return redirect("/")

        flash("Invalid username or password")
        return redirect("/login")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- REGISTER ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password required")
            return redirect("/register")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash("Registration successful. Please login.")
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            flash("User already exists")
            return redirect("/register")

    return render_template("register.html")

# ---------- DASHBOARD ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    # Add record
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        product = request.form.get("product", "").strip()
        quantity = safe_float(request.form.get("quantity"))
        unit_price = safe_float(request.form.get("unit_price"))
        paid = safe_float(request.form.get("paid"))
        date = request.form.get("date") or datetime.date.today().isoformat()
        due_date = request.form.get("due_date") or (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        payment_status = request.form.get("payment_status", "pending")

        if not name or not product:
            flash("Customer name and product are required")
            return redirect("/")

        total = quantity * unit_price
        loan = total - paid

        # Auto-create customer if not exists
        customer = conn.execute("SELECT * FROM customers WHERE full_name=?", (name,)).fetchone()
        if customer:
            customer_id = customer["id"]
        else:
            cur = conn.execute("""
                INSERT INTO customers(full_name,phone,address,note,created_at)
                VALUES(?,?,?,?,?)
            """, (name, "", "", "", datetime.date.today().isoformat()))
            customer_id = cur.lastrowid
            conn.commit()

        # Insert record
        conn.execute("""
            INSERT INTO records(customer_id,product,quantity,unit_price,total,paid,loan,date,due_date,payment_status)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (customer_id, product, quantity, unit_price, total, paid, loan, date, due_date, payment_status))
        conn.commit()
        flash(f"Record added for {name}")
        return redirect("/")

    # Search
    search = request.args.get("search")
    if search:
        records = conn.execute("""
            SELECT records.*, customers.full_name
            FROM records
            JOIN customers ON records.customer_id = customers.id
            WHERE customers.full_name LIKE ?
            ORDER BY records.id DESC
        """, ('%' + search + '%',)).fetchall()
    else:
        records = conn.execute("""
            SELECT records.*, customers.full_name
            FROM records
            JOIN customers ON records.customer_id = customers.id
            ORDER BY records.id DESC
        """).fetchall()

    total_sales = conn.execute("SELECT SUM(total) FROM records").fetchone()[0] or 0
    total_loans = conn.execute("SELECT SUM(loan) FROM records").fetchone()[0] or 0
    num_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] or 0
    conn.close()

    return render_template("index.html",
                           records=records,
                           total_sales=total_sales,
                           total_loans=total_loans,
                           num_customers=num_customers,
                           now_date=datetime.date.today().isoformat(),
                           due_date_default=(datetime.date.today() + datetime.timedelta(days=30)).isoformat())

# ---------- CUSTOMER PROFILE ----------

@app.route("/customer/<int:id>", methods=["GET","POST"])
def customer(id):
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action", "update_profile")
        
        if action == "update_profile":
            # Update customer profile
            phone = request.form["phone"]
            address = request.form["address"]
            note = request.form["note"]

            conn.execute("""
                UPDATE customers
                SET phone=?, address=?, note=?
                WHERE id=?
            """, (phone, address, note, id))
            conn.commit()
            flash("Profile updated successfully")
        
        elif action == "add_loan":
            # Add new past loan/record
            product = request.form.get("product", "").strip()
            quantity = safe_float(request.form.get("quantity"))
            unit_price = safe_float(request.form.get("unit_price"))
            paid = safe_float(request.form.get("paid"))
            date = request.form.get("date") or datetime.date.today().isoformat()
            due_date = request.form.get("due_date") or (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            payment_status = request.form.get("payment_status", "pending")

            if not product:
                flash("Product name is required")
                return redirect(f"/customer/{id}")

            total = quantity * unit_price
            loan = total - paid

            conn.execute("""
                INSERT INTO records(customer_id,product,quantity,unit_price,total,paid,loan,date,due_date,payment_status)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (id, product, quantity, unit_price, total, paid, loan, date, due_date, payment_status))
            conn.commit()
            flash("Past loan added successfully")

    customer = conn.execute("SELECT * FROM customers WHERE id=?", (id,)).fetchone()
    records = conn.execute("SELECT * FROM records WHERE customer_id=?", (id,)).fetchall()
    conn.close()

    return render_template("customer.html",
                           customer=customer,
                           records=records,
                           now_date=datetime.date.today().isoformat(),
                           due_date_default=(datetime.date.today() + datetime.timedelta(days=30)).isoformat())

# ---------- EDIT RECORD ----------

@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        product = request.form.get("product", "").strip()
        quantity = safe_float(request.form.get("quantity"))
        unit_price = safe_float(request.form.get("unit_price"))
        paid = safe_float(request.form.get("paid"))
        date = request.form.get("date") or datetime.date.today().isoformat()
        due_date = request.form.get("due_date")
        payment_status = request.form.get("payment_status", "pending")

        if not product:
            flash("Product name is required")
            return redirect(f"/edit/{id}")

        total = quantity * unit_price
        loan = total - paid

        conn.execute("""
            UPDATE records
            SET product=?, quantity=?, unit_price=?, total=?, paid=?, loan=?, date=?, due_date=?, payment_status=?
            WHERE id=?
        """, (product, quantity, unit_price, total, paid, loan, date, due_date, payment_status, id))
        conn.commit()
        conn.close()
        flash("Record updated successfully")
        return redirect("/")

    record = conn.execute("""
        SELECT records.*, customers.full_name
        FROM records
        JOIN customers ON records.customer_id = customers.id
        WHERE records.id=?
    """, (id,)).fetchone()
    conn.close()

    return render_template("edit.html", record=record, now_date=datetime.date.today().isoformat())

# ---------- DELETE ----------

@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# ---------- ANALYTICS & REPORTS ----------

@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    
    # Sales by month
    monthly_sales = conn.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(total) as sales, COUNT(*) as transactions
        FROM records
        WHERE date IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """).fetchall()

    # Top customers
    top_customers = conn.execute("""
        SELECT customers.full_name, SUM(records.total) as total_spent, COUNT(records.id) as transactions
        FROM records
        JOIN customers ON records.customer_id = customers.id
        GROUP BY records.customer_id
        ORDER BY total_spent DESC
        LIMIT 10
    """).fetchall()

    # Payment status summary
    payment_summary = conn.execute("""
        SELECT payment_status, COUNT(*) as count, SUM(loan) as total_loan
        FROM records
        GROUP BY payment_status
    """).fetchall()

    # Overdue loans
    from datetime import datetime, timedelta
    today = datetime.today().date()
    overdue_records = conn.execute("""
        SELECT records.id, customers.full_name, records.loan, records.due_date
        FROM records
        JOIN customers ON records.customer_id = customers.id
        WHERE payment_status = 'pending' AND due_date < ? AND loan > 0
        ORDER BY due_date ASC
    """, (today,)).fetchall()

    conn.close()

    return render_template("analytics.html",
                           monthly_sales=monthly_sales,
                           top_customers=top_customers,
                           payment_summary=payment_summary,
                           overdue_records=overdue_records)

# ---------- PRODUCTS ----------

@app.route("/products", methods=["GET", "POST"])
def products():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "").strip()
        price = safe_float(request.form.get("price"))
        stock = safe_float(request.form.get("stock"))

        if not name or not unit:
            flash("Product name and unit are required")
            return redirect("/products")

        try:
            conn.execute(
                "INSERT INTO products(name, unit, price, stock, created_at) VALUES(?,?,?,?,?)",
                (name, unit, price, stock, datetime.date.today().isoformat())
            )
            conn.commit()
            flash(f"Product '{name}' added successfully")
        except sqlite3.IntegrityError:
            flash("Product already exists")
        
        return redirect("/products")

    products_list = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()

    return render_template("products.html", products=products_list)

@app.route("/product/<int:id>/delete")
def delete_product(id):
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Product deleted")
    return redirect("/products")

# ---------- ADVANCED SEARCH & FILTERS ----------

@app.route("/search-advanced")
def search_advanced():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    customer_name = request.args.get("customer", "").strip()
    product_name = request.args.get("product", "").strip()
    payment_status = request.args.get("payment_status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = """
        SELECT records.*, customers.full_name
        FROM records
        JOIN customers ON records.customer_id = customers.id
        WHERE 1=1
    """
    params = []

    if customer_name:
        query += " AND customers.full_name LIKE ?"
        params.append(f"%{customer_name}%")
    if product_name:
        query += " AND records.product LIKE ?"
        params.append(f"%{product_name}%")
    if payment_status:
        query += " AND records.payment_status = ?"
        params.append(payment_status)
    if date_from:
        query += " AND records.date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND records.date <= ?"
        params.append(date_to)

    query += " ORDER BY records.id DESC"
    records = conn.execute(query, params).fetchall()

    conn.close()

    return render_template("search_advanced.html",
                           records=records,
                           customer_name=customer_name,
                           product_name=product_name,
                           payment_status=payment_status,
                           date_from=date_from,
                           date_to=date_to)

# ---------- CSV EXPORT ----------

@app.route("/export/csv")
def export_csv():
    if "user" not in session:
        return redirect("/login")

    from flask import make_response
    import csv
    from io import StringIO

    conn = get_db()
    records = conn.execute("""
        SELECT records.id, customers.full_name, records.product, records.quantity, 
               records.unit_price, records.total, records.paid, records.loan, 
               records.date, records.due_date, records.payment_status
        FROM records
        JOIN customers ON records.customer_id = customers.id
        ORDER BY records.date DESC
    """).fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Customer', 'Product', 'Quantity', 'Unit Price (RWF)', 
                     'Total (RWF)', 'Paid (RWF)', 'Loan (RWF)', 'Date', 'Due Date', 'Status'])
    
    for r in records:
        writer.writerow(r)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=store_records.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# ---------- RUN ----------

if __name__ == "__main__":
    app.run(debug=True)