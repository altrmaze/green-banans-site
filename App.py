# ============================================================
# GreenACC V1 - Full single-file Flask accounting system
# Features:
# Login, Admin/User permissions, Customers, Invoices,
# Quotations, Payroll, Dashboard, Print Invoice, SQLite database
# ============================================================

from flask import Flask, request, redirect, url_for, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, LoginManager, login_user,
    logout_user, login_required, current_user
)
from functools import wraps
from datetime import datetime

# ============================================================
# 1) APP SETUP
# ============================================================

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///greenacc.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ============================================================
# 2) DATABASE TABLES
# ============================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default="staff")


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(100))
    email = db.Column(db.String(150))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    invoice_type = db.Column(db.String(50), default="invoice")  # invoice or quotation
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="unpaid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("Customer")


class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(200), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    bonus = db.Column(db.Float, default=0)
    deduction = db.Column(db.Float, default=0)
    month = db.Column(db.String(50), nullable=False)


# ============================================================
# 3) LOGIN LOADER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================================
# 4) PERMISSION SYSTEM
# ============================================================

def permission_required(*roles):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.")
                return redirect(url_for("dashboard"))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper


# ============================================================
# 5) DESIGN TEMPLATE
# ============================================================

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GreenACC</title>
    <style>
        body { font-family: Arial; margin: 0; background: #f4f6f8; }
        .nav { background: #0b5d1e; color: white; padding: 15px; }
        .nav a { color: white; margin-right: 15px; text-decoration: none; font-weight: bold; }
        .container { padding: 25px; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
        input, textarea, select { width: 100%; padding: 10px; margin: 7px 0; }
        button { background: #0b5d1e; color: white; padding: 10px 18px; border: 0; cursor: pointer; }
        table { width: 100%; background: white; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 10px; }
        th { background: #0b5d1e; color: white; }
        .danger { color: red; }
        @media print {
            .nav, .no-print { display: none; }
            body { background: white; }
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="{{ url_for('dashboard') }}">Dashboard</a>
        <a href="{{ url_for('customers') }}">Customers</a>
        <a href="{{ url_for('invoices') }}">Invoices</a>
        <a href="{{ url_for('quotations') }}">Quotations</a>
        <a href="{{ url_for('payroll') }}">Payroll</a>
        {% if current_user.is_authenticated and current_user.role == 'admin' %}
            <a href="{{ url_for('users') }}">Users</a>
        {% endif %}
        {% if current_user.is_authenticated %}
            <a href="{{ url_for('logout') }}">Logout</a>
        {% endif %}
    </div>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="card danger">
                    {% for message in messages %}
                        <p>{{ message }}</p>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        {{ content|safe }}
    </div>
</body>
</html>
"""

def page(content, **kwargs):
    return render_template_string(BASE_HTML, content=render_template_string(content, **kwargs))


# ============================================================
# 6) HOME / LOGIN / LOGOUT
# ============================================================

@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Wrong username or password.")

    return page("""
    <div class="card">
        <h2>GreenACC Login</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Login</button>
        </form>
    </div>
    """)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ============================================================
# 7) DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    total_customers = Customer.query.count()
    total_invoices = Invoice.query.filter_by(invoice_type="invoice").count()
    total_quotations = Invoice.query.filter_by(invoice_type="quotation").count()
    total_sales = db.session.query(db.func.sum(Invoice.amount)).filter_by(invoice_type="invoice").scalar() or 0

    return page("""
    <h1>GreenACC Dashboard</h1>

    <div class="card">
        <h3>Welcome, {{ current_user.username }}</h3>
        <p>Your role: <b>{{ current_user.role }}</b></p>
    </div>

    <div class="card">
        <h3>Summary</h3>
        <p>Total Customers: {{ total_customers }}</p>
        <p>Total Invoices: {{ total_invoices }}</p>
        <p>Total Quotations: {{ total_quotations }}</p>
        <p>Total Sales: {{ total_sales }}</p>
    </div>
    """, total_customers=total_customers, total_invoices=total_invoices,
       total_quotations=total_quotations, total_sales=total_sales)


# ============================================================
# 8) CUSTOMERS
# Permission: admin, accountant, sales
# ============================================================

@app.route("/customers", methods=["GET", "POST"])
@login_required
@permission_required("admin", "accountant", "sales")
def customers():
    if request.method == "POST":
        customer = Customer(
            name=request.form["name"],
            phone=request.form["phone"],
            email=request.form["email"],
            address=request.form["address"],
            notes=request.form["notes"]
        )
        db.session.add(customer)
        db.session.commit()
        return redirect(url_for("customers"))

    customers_list = Customer.query.all()

    return page("""
    <h2>Customers</h2>

    <div class="card">
        <h3>Add Customer</h3>
        <form method="POST">
            <input name="name" placeholder="Customer Name" required>
            <input name="phone" placeholder="Phone">
            <input name="email" placeholder="Email">
            <textarea name="address" placeholder="Address"></textarea>
            <textarea name="notes" placeholder="Notes"></textarea>
            <button>Add Customer</button>
        </form>
    </div>

    <table>
        <tr>
            <th>ID</th><th>Name</th><th>Phone</th><th>Email</th><th>Address</th>
        </tr>
        {% for c in customers_list %}
        <tr>
            <td>{{ c.id }}</td>
            <td>{{ c.name }}</td>
            <td>{{ c.phone }}</td>
            <td>{{ c.email }}</td>
            <td>{{ c.address }}</td>
        </tr>
        {% endfor %}
    </table>
    """, customers_list=customers_list)


# ============================================================
# 9) INVOICES
# Permission: admin, accountant, sales
# ============================================================

@app.route("/invoices", methods=["GET", "POST"])
@login_required
@permission_required("admin", "accountant", "sales")
def invoices():
    customers_list = Customer.query.all()

    if request.method == "POST":
        invoice = Invoice(
            customer_id=request.form["customer_id"],
            invoice_type="invoice",
            description=request.form["description"],
            amount=float(request.form["amount"]),
            status=request.form["status"]
        )
        db.session.add(invoice)
        db.session.commit()
        return redirect(url_for("invoices"))

    invoices_list = Invoice.query.filter_by(invoice_type="invoice").all()

    return page("""
    <h2>Invoices</h2>

    <div class="card">
        <h3>Create Invoice</h3>
        <form method="POST">
            <select name="customer_id" required>
                {% for c in customers_list %}
                    <option value="{{ c.id }}">{{ c.name }}</option>
                {% endfor %}
            </select>
            <textarea name="description" placeholder="Invoice Description" required></textarea>
            <input name="amount" type="number" step="0.01" placeholder="Amount" required>
            <select name="status">
                <option value="unpaid">Unpaid</option>
                <option value="paid">Paid</option>
                <option value="partial">Partial</option>
            </select>
            <button>Create Invoice</button>
        </form>
    </div>

    <table>
        <tr>
            <th>ID</th><th>Customer</th><th>Description</th><th>Amount</th><th>Status</th><th>Print</th>
        </tr>
        {% for i in invoices_list %}
        <tr>
            <td>{{ i.id }}</td>
            <td>{{ i.customer.name }}</td>
            <td>{{ i.description }}</td>
            <td>{{ i.amount }}</td>
            <td>{{ i.status }}</td>
            <td><a href="{{ url_for('print_invoice', invoice_id=i.id) }}">Print</a></td>
        </tr>
        {% endfor %}
    </table>
    """, customers_list=customers_list, invoices_list=invoices_list)


# ============================================================
# 10) QUOTATIONS
# Permission: admin, accountant, sales
# ============================================================

@app.route("/quotations", methods=["GET", "POST"])
@login_required
@permission_required("admin", "accountant", "sales")
def quotations():
    customers_list = Customer.query.all()

    if request.method == "POST":
        quotation = Invoice(
            customer_id=request.form["customer_id"],
            invoice_type="quotation",
            description=request.form["description"],
            amount=float(request.form["amount"]),
            status="quotation"
        )
        db.session.add(quotation)
        db.session.commit()
        return redirect(url_for("quotations"))

    quotations_list = Invoice.query.filter_by(invoice_type="quotation").all()

    return page("""
    <h2>Quotations</h2>

    <div class="card">
        <h3>Create Quotation</h3>
        <form method="POST">
            <select name="customer_id" required>
                {% for c in customers_list %}
                    <option value="{{ c.id }}">{{ c.name }}</option>
                {% endfor %}
            </select>
            <textarea name="description" placeholder="Quotation Description" required></textarea>
            <input name="amount" type="number" step="0.01" placeholder="Amount" required>
            <button>Create Quotation</button>
        </form>
    </div>

    <table>
        <tr>
            <th>ID</th><th>Customer</th><th>Description</th><th>Amount</th><th>Print</th>
        </tr>
        {% for q in quotations_list %}
        <tr>
            <td>{{ q.id }}</td>
            <td>{{ q.customer.name }}</td>
            <td>{{ q.description }}</td>
            <td>{{ q.amount }}</td>
            <td><a href="{{ url_for('print_invoice', invoice_id=q.id) }}">Print</a></td>
        </tr>
        {% endfor %}
    </table>
    """, customers_list=customers_list, quotations_list=quotations_list)


# ============================================================
# 11) PRINT INVOICE / QUOTATION
# ============================================================

@app.route("/print/<int:invoice_id>")
@login_required
def print_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    return page("""
    <div class="card">
        <h1>GreenACC</h1>
        <h2>{{ invoice.invoice_type|upper }}</h2>

        <p><b>Document No:</b> {{ invoice.id }}</p>
        <p><b>Date:</b> {{ invoice.created_at.strftime('%Y-%m-%d') }}</p>

        <hr>

        <h3>Customer</h3>
        <p><b>Name:</b> {{ invoice.customer.name }}</p>
        <p><b>Phone:</b> {{ invoice.customer.phone }}</p>
        <p><b>Email:</b> {{ invoice.customer.email }}</p>
        <p><b>Address:</b> {{ invoice.customer.address }}</p>

        <hr>

        <h3>Description</h3>
        <p>{{ invoice.description }}</p>

        <h2>Total: {{ invoice.amount }}</h2>
        <p>Status: {{ invoice.status }}</p>

        <button class="no-print" onclick="window.print()">Print</button>
    </div>
    """, invoice=invoice)


# ============================================================
# 12) PAYROLL
# Permission: admin, accountant
# ============================================================

@app.route("/payroll", methods=["GET", "POST"])
@login_required
@permission_required("admin", "accountant")
def payroll():
    if request.method == "POST":
        record = Payroll(
            employee_name=request.form["employee_name"],
            salary=float(request.form["salary"]),
            bonus=float(request.form["bonus"] or 0),
            deduction=float(request.form["deduction"] or 0),
            month=request.form["month"]
        )
        db.session.add(record)
        db.session.commit()
        return redirect(url_for("payroll"))

    payroll_list = Payroll.query.all()

    return page("""
    <h2>Payroll</h2>

    <div class="card">
        <h3>Add Payroll</h3>
        <form method="POST">
            <input name="employee_name" placeholder="Employee Name" required>
            <input name="salary" type="number" step="0.01" placeholder="Salary" required>
            <input name="bonus" type="number" step="0.01" placeholder="Bonus" value="0">
            <input name="deduction" type="number" step="0.01" placeholder="Deduction" value="0">
            <input name="month" placeholder="Month, example: January 2026" required>
            <button>Add Payroll</button>
        </form>
    </div>

    <table>
        <tr>
            <th>ID</th><th>Employee</th><th>Salary</th><th>Bonus</th><th>Deduction</th><th>Net</th><th>Month</th>
        </tr>
        {% for p in payroll_list %}
        <tr>
            <td>{{ p.id }}</td>
            <td>{{ p.employee_name }}</td>
            <td>{{ p.salary }}</td>
            <td>{{ p.bonus }}</td>
            <td>{{ p.deduction }}</td>
            <td>{{ p.salary + p.bonus - p.deduction }}</td>
            <td>{{ p.month }}</td>
        </tr>
        {% endfor %}
    </table>
    """, payroll_list=payroll_list)


# ============================================================
# 13) USER MANAGEMENT
# Permission: admin only
# ============================================================

@app.route("/users", methods=["GET", "POST"])
@login_required
@permission_required("admin")
def users():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=request.form["password"],
            role=request.form["role"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("users"))

    users_list = User.query.all()

    return page("""
    <h2>User Management</h2>

    <div class="card">
        <h3>Add User</h3>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" placeholder="Password" required>
            <select name="role">
                <option value="admin">Admin - Full Access</option>
                <option value="accountant">Accountant - Accounting + Payroll</option>
                <option value="sales">Sales - Customers + Invoices</option>
                <option value="staff">Staff - Dashboard Only</option>
            </select>
            <button>Add User</button>
        </form>
    </div>

    <table>
        <tr>
            <th>ID</th><th>Username</th><th>Role</th>
        </tr>
        {% for u in users_list %}
        <tr>
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.role }}</td>
        </tr>
        {% endfor %}
    </table>
    """, users_list=users_list)


# ============================================================
# 14) CREATE DATABASE AND DEFAULT ADMIN
# ============================================================

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            password="admin123",
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()


# ============================================================
# 15) RUN APP
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
