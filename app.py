from flask import Flask, render_template, request, redirect
import sqlite3

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
    )
    """)
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

        total = quantity * unit_price
        loan = total - paid

        conn.execute("""
        INSERT INTO records (full_name, product, quantity, unit_price, total, paid, loan)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, product, quantity, unit_price, total, paid, loan))
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

    return render_template("index.html",
                           records=records,
                           total_sales=total_sales,
                           total_loans=total_loans)


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

        total = quantity * unit_price
        loan = total - paid

        conn.execute("""
        UPDATE records
        SET full_name=?, product=?, quantity=?, unit_price=?, total=?, paid=?, loan=?
        WHERE id=?
        """, (name, product, quantity, unit_price, total, paid, loan, id))
        conn.commit()
        conn.close()
        return redirect("/")

    record = conn.execute("SELECT * FROM records WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template("edit.html", record=record)


if __name__ == "__main__":
    app.run(debug=True)