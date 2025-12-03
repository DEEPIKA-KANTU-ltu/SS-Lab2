from flask import Flask, request, redirect, render_template, flash, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production"

# Separate DB paths
DB_PATH_USERS = "users_data.db"
DB_PATH_ADMINS = "admins_data.db"

# MongoDB connection
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["stroke_app"]
feedback_collection = mongo_db["feedbacks"]
history_collection = mongo_db["medical_history"]

# -----------------------------
# Database initialization
# -----------------------------
def init_db():
    # Users DB
    conn_users = sqlite3.connect(DB_PATH_USERS)
    cursor_users = conn_users.cursor()
    cursor_users.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            gender TEXT,
            age INTEGER,
            work_type TEXT,
            residence_type TEXT,
            ever_married TEXT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            hypertension INTEGER,
            heart_disease INTEGER,
            avg_glucose_level REAL,
            bmi REAL,
            smoking_status TEXT,
            stroke INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor_users.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_noncase
        ON users (lower(email));
    """)
    conn_users.commit()
    conn_users.close()

    # Admins DB
    conn_admins = sqlite3.connect(DB_PATH_ADMINS)
    cursor_admins = conn_admins.cursor()
    cursor_admins.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            age TEXT,
            gender TEXT,
            department TEXT,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            contact TEXT
        )
    """)
    conn_admins.commit()
    conn_admins.close()

# -----------------------------
# Routes: Registration
# -----------------------------
@app.route("/")
def register():
    return render_template("register2.html")

@app.route("/register", methods=["POST"])
def do_register():
    role = request.form.get("role", "user").strip().lower()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

    try:
        if role == "user":
            conn = sqlite3.connect(DB_PATH_USERS)
            cursor = conn.cursor()

            gender = request.form.get("gender", "").strip()
            age = request.form.get("age", "").strip()
            work_type = request.form.get("work_type", "").strip()
            residence_type = request.form.get("residence_type", "").strip()
            ever_married = request.form.get("ever_married", "").strip()

            cursor.execute("SELECT 1 FROM users WHERE lower(email)=lower(?)", (email,))
            if cursor.fetchone():
                flash("This email is already registered as a user.")
                conn.close()
                return redirect(url_for("login"))

            cursor.execute("""
                INSERT INTO users (first_name, last_name, gender, age, work_type, residence_type, ever_married, email, password, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (first_name, last_name, gender, age, work_type, residence_type, ever_married, email, hashed_password, role))

        elif role == "admin":
            conn = sqlite3.connect(DB_PATH_ADMINS)
            cursor = conn.cursor()

            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            department = request.form.get("department", "").strip()
            contact = request.form.get("contact", "").strip()

            cursor.execute("SELECT 1 FROM admins WHERE lower(email)=lower(?)", (email,))
            if cursor.fetchone():
                flash("This email is already registered as an admin.")
                conn.close()
                return redirect(url_for("login"))

            cursor.execute("""
                INSERT INTO admins (first_name, last_name, age, gender, department, email, password, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (first_name, last_name, age, gender, department, email, hashed_password, contact))

        conn.commit()
        flash("Registration successful! Please log in.")

    except sqlite3.IntegrityError:
        flash("This email is already registered.")
    finally:
        conn.close()

    return redirect(url_for("login"))

# -----------------------------
# Routes: Login / Logout
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    email = request.form.get("email", "").strip()
    password = request.form.get("password","")
    role = request.form.get("role", "user").strip().lower()

    if not (email and password):
        flash("Please enter both email and password.")
        return redirect(url_for("login"))
    
    if role == "user":
        conn = sqlite3.connect(DB_PATH_USERS)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, first_name, last_name, email, password, role
            FROM users 
            WHERE lower(email) = lower(?)
        """, (email,))
        row = cursor.fetchone()
        conn.close()

    elif role == "admin":
        conn = sqlite3.connect(DB_PATH_ADMINS)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, first_name, last_name, email, password
            FROM admins 
            WHERE lower(email) = lower(?)
        """, (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            row = (*row, "admin")  # add role manually

    if not row:
        flash("Invalid email or password.")
        return redirect(url_for("login"))
    
    user_id, first_name, last_name, user_email, password_hash, role = row
    if not check_password_hash(password_hash, password):
        flash("Invalid email or password.")
        return redirect(url_for("login"))
    
    session["user_id"] = user_id
    session["user_email"] = user_email
    session["user_name"] = f"{first_name} {last_name}"
    session["role"] = role
    flash(f"Welcome back, {first_name}!")

    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

# -----------------------------
# Admin Dashboard & Routes
# -----------------------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") == "admin":
        return render_template("admin_dashboard.html")
    else:
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, gender, age, work_type, residence_type, ever_married, email,
               hypertension, heart_disease, avg_glucose_level, bmi, smoking_status, stroke, created_at
        FROM users ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return render_template("admin_users.html", users=rows)

@app.route("/admin/user/<int:user_id>/info")
def admin_user_info(user_id):
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, age, gender, bmi, avg_glucose_level,
               hypertension, heart_disease, smoking_status, stroke
        FROM users WHERE id=?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("admin_user_info.html", user=user)

# -----------------------------
# User Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to continue")
        return redirect(url_for("login"))
    return render_template('dashboard.html')

# -----------------------------
# User Management Routes
# -----------------------------
@app.route("/users")
def users():
    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, gender, age, work_type, residence_type, ever_married, email,
               hypertension, heart_disease, avg_glucose_level, bmi, smoking_status, stroke, created_at
        FROM users ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return render_template

@app.route("/admin/analyze/<int:user_id>")
def admin_analyze(user_id):
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, age, gender, 
               bmi, avg_glucose_level, hypertension, heart_disease
        FROM users WHERE id=?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("admin_analyze.html", user=user)

# (delete_user, edit_user, add_info, analyze, history, feedback remain the same but use DB_PATH_USERS)

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=False)
