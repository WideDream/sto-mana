from flask import Flask, render_template, request, redirect
import sqlite3
import datetime

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        product TEXT,
        quantity REAL,
        unit_price REAL,
        total REAL,
        paid REAL,
        loan REAL
        ,date TEXT
    )
    """)
    conn.commit()
    # If an older DB exists without the `date` column, add it.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()]
    if 'date' not in cols:
        try:
            conn.execute("ALTER TABLE records ADD COLUMN date TEXT")
        except Exception:
            pass
    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        product = request.form["product"]
        quantity = float(request.form["quantity"])
        unit_price = float(request.form["unit_price"])
        paid = float(request.form["paid"])
        date = request.form.get("date") or datetime.date.today().isoformat()

        total = quantity * unit_price
        loan = total - paid

        conn.execute("""
        INSERT INTO records (full_name, product, quantity, unit_price, total, paid, loan, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, product, quantity, unit_price, total, paid, loan, date))
        conn.commit()
        return redirect("/")

    search = request.args.get("search")
    if search:
        records = conn.execute(
            "SELECT * FROM records WHERE full_name LIKE ?",
            ('%' + search + '%',)
        ).fetchall()
    else:
        records = conn.execute("SELECT * FROM records").fetchall()

    total_sales = conn.execute("SELECT SUM(total) FROM records").fetchone()[0] or 0
    total_loans = conn.execute("SELECT SUM(loan) FROM records").fetchone()[0] or 0

    conn.close()

    now_date = datetime.date.today().isoformat()

    return render_template("index.html",
                           records=records,
                           total_sales=total_sales,
                           total_loans=total_loans,
                           now_date=now_date)


@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        product = request.form["product"]
        quantity = float(request.form["quantity"])
        unit_price = float(request.form["unit_price"])
        paid = float(request.form["paid"])
        date = request.form.get("date") or datetime.date.today().isoformat()

        total = quantity * unit_price
        loan = total - paid

        conn.execute("""
        UPDATE records
        SET full_name=?, product=?, quantity=?, unit_price=?, total=?, paid=?, loan=?, date=?
        WHERE id=?
        """, (name, product, quantity, unit_price, total, paid, loan, date, id))
        conn.commit()
        conn.close()
        return redirect("/")

    record = conn.execute("SELECT * FROM records WHERE id=?", (id,)).fetchone()
    conn.close()

    now_date = datetime.date.today().isoformat()
    return render_template("edit.html", record=record, now_date=now_date)