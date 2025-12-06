from flask import Flask, request, redirect, render_template, flash, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pymongo import MongoClient
from datetime import datetime
import couchdb
import os
import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production"

# Separate DB paths
DB_PATH_USERS = "users_data.db"
DB_PATH_ADMINS = "admins_data.db"



def compute_risk(user_row):
    age = user_row["age"] or 0
    bmi = float(user_row["bmi"] or 0)
    glucose = float(user_row["avg_glucose_level"] or 0)
    hypertension = int(user_row["hypertension"] or 0)
    heart_disease = int(user_row["heart_disease"] or 0)

   

    score = 0.0
    if age >= 60: score += 0.25
    elif age >= 45: score += 0.15
    elif age >= 30: score += 0.08

    if bmi >= 30: score += 0.15
    elif bmi >= 25: score += 0.08

    if hypertension: score += 0.2
    if heart_disease: score += 0.2

    if glucose >= 126: score += 0.15
    elif glucose >= 100: score += 0.08

    return round(min(score, 1.0), 3)


# -----------------------------
# Database initialization
# -----------------------------
def init_db():
    # Users DB
    conn_users = sqlite3.connect(DB_PATH_USERS)
    cursor_users = conn_users.cursor()

    # Create users table (with risk_score if new)
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            risk_score REAL DEFAULT 0
        )
    """)

    # Case-insensitive unique index on email
    cursor_users.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_noncase
        ON users(email COLLATE NOCASE)
    """)

    # --- ALTER TABLE if risk_score column is missing ---
    cursor_users.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor_users.fetchall()]
    if "risk_score" not in columns:
        cursor_users.execute("ALTER TABLE users ADD COLUMN risk_score REAL DEFAULT 0")

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
    return render_template("register.html")
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
    python        FROM users 
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
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()

    # Total patients
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    # High risk patients (risk_score ≥ 0.7)
    cursor.execute("SELECT COUNT(*) FROM users WHERE risk_score >= 0.7")
    high_risk = cursor.fetchone()[0]

    # Average risk
    cursor.execute("SELECT AVG(risk_score) FROM users")
    avg_risk = cursor.fetchone()[0] or 0

    # Recent entries (last 7 days)
    cursor.execute("""
        SELECT id, first_name, last_name, risk_score, created_at
        FROM users
        WHERE datetime(created_at) >= datetime('now','-7 days')
        ORDER BY created_at DESC LIMIT 5
    """)
    recent = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total=total,
        high_risk=high_risk,
        avg_risk=avg_risk,
        recent=recent
    )

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
        SELECT id, first_name, last_name, age, gender, work_type, residence_type, 
               ever_married, email, bmi, avg_glucose_level, hypertension, heart_disease, 
               smoking_status, stroke
        FROM users WHERE id=?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        flash("User not found.")
        return redirect(url_for("admin_users"))

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
       SELECT id, first_name, last_name, age, gender, work_type, residence_type,
       ever_married, bmi, avg_glucose_level, hypertension, heart_disease,
       smoking_status, stroke
        FROM users WHERE id=?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("admin_analyze.html", user=user)

# (delete_user, edit_user, add_info, analyze, history, feedback remain the same but use DB_PATH_USERS)

@app.route("/add_info", methods=["GET", "POST"])
def add_info():
    # Ensure only logged-in users can access
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        # Collect form data
        hypertension = request.form.get("hypertension")
        heart_disease = request.form.get("heart_disease")
        avg_glucose_level = request.form.get("avg_glucose_level")
        bmi = request.form.get("bmi")   
        smoking_status = request.form.get("smoking_status")
        stroke = request.form.get("stroke")

        # Update database
        conn = sqlite3.connect(DB_PATH_USERS)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET hypertension=?, heart_disease=?, avg_glucose_level=?, bmi=?, 
                smoking_status=?, stroke=?
            WHERE id=?
        """, (hypertension, heart_disease, avg_glucose_level, bmi,
              smoking_status, stroke, user_id))
        conn.commit()
        conn.close()

        flash("Medical information updated successfully.")
        return redirect(url_for("dashboard"))
    
    # GET → load existing values
    conn = sqlite3.connect(DB_PATH_USERS)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    # GET request → render the form
    return render_template("add_info.html", user=user)



couch = couchdb.Server("http://Deepika:deepika20051%24@127.0.0.1:5984/")
db_name = "user_feedback"
if db_name in couch:
    feedback_db = couch[db_name]
else:
    feedback_db = couch.create(db_name)

# Patient History DB
if "patient_history" in couch:
    history_db = couch["patient_history"]
else:
    history_db = couch.create("patient_history")

# -----------------------------
# Risk calculation
# -----------------------------
def compute_risk(user_row):
    age = int(user_row["age"] or 0)
    bmi = float(user_row["bmi"] or 0)
    glucose = float(user_row["avg_glucose_level"] or 0)
    hypertension = int(user_row["hypertension"] or 0)
    heart_disease = int(user_row["heart_disease"] or 0)

    score = 0.0
    if age >= 60: score += 0.25
    elif age >= 45: score += 0.15
    elif age >= 30: score += 0.08

    if bmi >= 30: score += 0.15
    elif bmi >= 25: score += 0.08

    if hypertension: score += 0.2
    if heart_disease: score += 0.2

    if glucose >= 126: score += 0.15
    elif glucose >= 100: score += 0.08

    return round(min(score, 1.0), 3)


# -----------------------------
# Analyze route
# -----------------------------

def map_values(user_row):
    return {
        "hypertension": "Have Hypertension" if int(user_row["hypertension"] or 0) == 1 else "No Hypertension",
        "heart_disease": "Have Heart Disease" if int(user_row["heart_disease"] or 0) == 1 else "No Heart Disease",
        "stroke": "Had Stroke" if int(user_row["stroke"] or 0) == 1 else "No Stroke",
        "smoking_status": {
            "0": "Former Smoker",
            "1": "Never Smoked",
            "2": "Current Smoker",
            "3": "Unknown"
        }.get(str(user_row["smoking_status"]), "N/A")
    }


@app.route("/analyze")
def analyze():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # --- Fetch user info from SQLite ---
    conn = sqlite3.connect(DB_PATH_USERS)
    conn.row_factory = sqlite3.Row   # allow dict-like access
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, age, gender, work_type, residence_type,
               ever_married, bmi, avg_glucose_level, hypertension, heart_disease,
               smoking_status, stroke
        FROM users WHERE id=?
    """, (user_id,))
    user_row = cursor.fetchone()
    conn.close()

    if not user_row:
        flash("User data not found.")
        return redirect(url_for("dashboard"))

    # --- Compute risk ---
    risk_score = compute_risk(user_row)

    # --- Update DB with risk score ---
    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET risk_score=? WHERE id=?", (risk_score, user_id))
    conn.commit()
    conn.close()

    # --- Categorize risk ---
    if risk_score >= 0.7:
        category, color = "High", "#dc3545"
    elif risk_score >= 0.4:
        category, color = "Medium", "#ecc348"
    else:
        category, color = "Low", "#28a745"

    # --- Fetch feedback from CouchDB ---
    feedback = []
    for row in feedback_db.view('_all_docs', include_docs=True):
        doc = row.doc
        if str(doc.get("user_id")) == str(user_id):
            feedback.append({
                "rating": doc.get("rating"),
                "comment": doc.get("comment"),
                "timestamp": doc.get("timestamp")
            })
#apply mapping
    mapped = map_values(user_row)

    doc = {
        "user_id": user_id,
        "first_name": user_row["first_name"],
        "last_name": user_row["last_name"],
        "age": user_row["age"],
        "gender": user_row["gender"],
        "work_type": user_row["work_type"],
        "residence_type": user_row["residence_type"],
        "ever_married": user_row["ever_married"],
        "medical_data": {
            "bmi": user_row["bmi"],
            "avg_glucose_level": user_row["avg_glucose_level"],
            "hypertension": mapped["hypertension"],
            "heart_disease": mapped["heart_disease"],
            "smoking_status": mapped["smoking_status"],
            "stroke": mapped["stroke"],
        },
        "risk_score": risk_score,
        "timestamp": datetime.datetime.now().isoformat()
    }
    history_db.save(doc)


    # --- Render template ---
    return render_template(
        "analyze.html",
        user=user_row,
        risk_score=risk_score,
        category=category,
        color=color,
        feedback=feedback
    )


# -----------------------------
# Feedback route
# -----------------------------
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    if request.method == "POST":
        rating = request.form.get("rating")
        comment = request.form.get("comment")

        # Fetch latest risk analysis for this user
        conn = sqlite3.connect(DB_PATH_USERS)
        cursor = conn.cursor()
        cursor.execute("SELECT risk_score FROM users WHERE id=?", (session["user_id"],))
        row = cursor.fetchone()
        conn.close()

        risk_score = row[0] if row else 0.0
        if risk_score >= 0.7:
            category, color = "High", "#dc3545"
        elif risk_score >= 0.4:
            category, color = "Medium", "#ffc107"
        else:
            category, color = "Low", "#28a745"

        # Create JSON document for CouchDB
        doc = {
            "user_id": session["user_id"],
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.datetime.now().isoformat(),
            "analysis": {
                "risk_score": risk_score,
                "category": category,
                "color": color
            }
        }

        feedback_db.save(doc)

        flash("Thank you for your feedback!")
        return redirect(url_for("dashboard"))

    return render_template("feedback.html")
def save_patient_snapshot(user_id, patient_data):
    mapped = {
        "hypertension": "Have Hypertension" if str(patient_data.get("hypertension")) == "1" else "No Hypertension",
        "heart_disease": "Have Heart Disease" if str(patient_data.get("heart_disease")) == "1" else "No Heart Disease",
        "stroke": "Had Stroke" if str(patient_data.get("stroke")) == "1" else "No Stroke",
        "smoking_status": {
            "0": "Former Smoker",
            "1": "Never Smoked",
            "2": "Current Smoker",
            "3": "Unknown"
        }.get(str(patient_data.get("smoking_status")), "N/A")
    }    
    doc = {
        "user_id": user_id,
        #"action": action,  # update or delete
        "first_name": patient_data.get("first_name"),
        "last_name": patient_data.get("last_name"),
        "age": patient_data.get("age"),
        "gender": patient_data.get("gender"),
        "work_type": patient_data.get("work_type"),
        "residence_type": patient_data.get("residence_type"),
        "ever_married": patient_data.get("ever_married"),
        "medical_data": {
            "hypertension": mapped["hypertension"],
            "heart_disease": mapped["heart_disease"],
            "avg_glucose_level": patient_data.get("avg_glucose_level"),
            "bmi": patient_data.get("bmi"),
            "smoking_status": mapped["smoking_status"],
            "stroke": mapped["stroke"],
        },
        "risk_score": patient_data.get("risk_score"),
        "timestamp": datetime.datetime.now().isoformat()
    }
    history_db.save(doc)


@app.route("/history")
def history():
    # Ensure only logged-in users can access
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch snapshots from CouchDB for this user
    records = []
    for row in history_db.view('_all_docs', include_docs=True):
        doc = row.doc
        if str(doc.get("user_id")) == str(user_id):
            records.append(doc)

    # Sort by timestamp (latest first)
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return render_template("history.html", records=records)


import os, couchdb
couch = couchdb.Server(os.getenv("COUCHDB_URL"))

# Connect to CouchDB server

couch = couchdb.Server("http://Deepika:deepika20051$@127.0.0.1:5984/")

db_name = "user_feedback"

if db_name in couch:
    db = couch[db_name]
else:
    db = couch.create(db_name)



@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    # Ensure only logged-in users can edit their own info
    if "user_id" not in session or session["user_id"] != user_id:
        flash("Access denied.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        work_type = request.form.get("work-type")
        residence_type = request.form.get("residence_type")
        ever_married = request.form.get("ever_married")
        email = request.form.get("email")
        password = request.form.get("password")

        # Update user info
        if password:  # if new password provided
            cursor.execute("""
                UPDATE users
                SET first_name=?, last_name=?, age=?, gender=?, work_type=?, residence_type=?, 
                    ever_married=?, email=?, password=?
                WHERE id=?
            """, (first_name, last_name, age, gender, work_type, residence_type,
                  ever_married, email, password, user_id))
        else:  # keep existing password
            cursor.execute("""
                UPDATE users
                SET first_name=?, last_name=?, age=?, gender=?, work_type=?, residence_type=?, 
                    ever_married=?, email=?
                WHERE id=?
            """, (first_name, last_name, age, gender, work_type, residence_type,
                  ever_married, email, user_id))

        conn.commit()
        conn.close()

        flash("Personal details updated successfully.")
        return redirect(url_for("dashboard"))

    # GET → load user info
    cursor.execute("""
        SELECT id, first_name, last_name, age, gender, work_type, residence_type, 
               ever_married, email
        FROM users WHERE id=?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        flash("User not found.")
        return redirect(url_for("dashboard"))

    return render_template("edit_user.html", user=user)


# -----------------------------
# Admin: Edit Personal Info
# -----------------------------
@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
def admin_edit_user(user_id):
    if session.get("role") != "admin":
        #flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        work_type = request.form.get("work_type")
        residence_type = request.form.get("residence_type")
        ever_married = request.form.get("ever_married")
        email = request.form.get("email")
       

        cursor.execute("""
            UPDATE users
            SET first_name=?, last_name=?, age=?, gender=?, work_type=?, residence_type=?, 
                ever_married=?, email=?
            WHERE id=?
        """, (first_name, last_name, age, gender, work_type, residence_type,
              ever_married, email, user_id))
        conn.commit()
        conn.close()


  # Fetch updated row and save snapshot
        conn = sqlite3.connect(DB_PATH_USERS)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        updated_user = cursor.fetchone()
        conn.close()

        # Compute risk score
        risk_score = compute_risk(updated_user)

        # Update SQLite with risk score
        conn = sqlite3.connect(DB_PATH_USERS)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET risk_score=? WHERE id=?", (risk_score, user_id))
        conn.commit()
        conn.close()

        # Save snapshot with risk score
        user_dict = dict(updated_user)
        user_dict["risk_score"] = risk_score
        save_patient_snapshot(user_id, user_dict)

        flash("User personal details updated successfully.")
        return redirect(url_for("admin_users"))

    # GET → load user info
    cursor.execute("SELECT id, first_name, last_name, age, gender, work_type, residence_type, ever_married, email FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template("edit_user.html", user=user)


# -----------------------------
# Admin: Edit Medical Info
# -----------------------------

@app.route("/admin/user/<int:user_id>/medical", methods=["GET", "POST"])
def admin_edit_medical(user_id):
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()

    if request.method == "POST":
        hypertension = request.form.get("hypertension")
        heart_disease = request.form.get("heart_disease")
        avg_glucose_level = request.form.get("avg_glucose_level")
        bmi = request.form.get("bmi")  
        smoking_status = request.form.get("smoking_status")
        stroke = request.form.get("stroke")

        cursor.execute("""
            UPDATE users
            SET hypertension=?, heart_disease=?, avg_glucose_level=?, bmi=?, 
                smoking_status=?, stroke=?
            WHERE id=?
        """, (hypertension, heart_disease, avg_glucose_level, bmi,
              smoking_status, stroke, user_id))
        conn.commit()
        conn.close()

        # Fetch updated row
        conn = sqlite3.connect(DB_PATH_USERS)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        updated_user = cursor.fetchone()
        conn.close()

        # Compute risk score
        risk_score = compute_risk(updated_user)

        # Update SQLite with risk score
        conn = sqlite3.connect(DB_PATH_USERS)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET risk_score=? WHERE id=?", (risk_score, user_id))
        conn.commit()
        conn.close()

        # Save snapshot with risk score
        user_dict = dict(updated_user)
        user_dict["risk_score"] = risk_score
        save_patient_snapshot(user_id, user_dict)

        flash("User medical information updated successfully.")
        return redirect(url_for("admin_users"))

    # GET → load medical info
    cursor.execute("SELECT id, hypertension, heart_disease, avg_glucose_level, bmi, smoking_status, stroke FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template("add_info.html", user=user)


#admin feedback
@app.route("/admin/feedbacks")
def admin_feedbacks():
    # Only allow admins
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    feedback_list = []
    for row in feedback_db.view('_all_docs', include_docs=True):
        doc = row.doc
        feedback_list.append({
            "user_id": doc.get("user_id"),
            "rating": doc.get("rating"),
            "comment": doc.get("comment"),
            "timestamp": doc.get("timestamp"),
            "analysis": doc.get("analysis")  # optional if you stored risk snapshot
        })

    return render_template("admin_feedbacks.html", feedbacks=feedback_list)
#patient history
@app.route("/admin/history")
def admin_history():
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    history_list = []
    for row in history_db.view('_all_docs', include_docs=True):
        doc = row.doc
        med = doc.get("medical_data", {})
        history_list.append({
            "user_id": doc.get("user_id"),
            "first_name": doc.get("first_name"),
            "last_name": doc.get("last_name"),
            "age": doc.get("age"),
            "gender": doc.get("gender"),
            "work_type": doc.get("work_type"),
            "residence_type": doc.get("residence_type"),
            "ever_married": doc.get("ever_married"),
            "hypertension": med.get("hypertension"),
            "heart_disease": med.get("heart_disease"),
            "avg_glucose_level": med.get("avg_glucose_level"),
            "bmi": med.get("bmi"),
            "smoking_status": med.get("smoking_status"),
            "stroke": med.get("stroke"),
            "risk_score": doc.get("risk_score"),
            "timestamp": doc.get("timestamp")
        })

    history_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return render_template("admin_history.html", history=history_list)


# -----------------------------
# Admin: Delete User
# -----------------------------
@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    if session.get("role") != "admin":
        flash("Access denied. Admins only.")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH_USERS)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    flash("User deleted successfully.")
    return redirect(url_for("admin_users"))


# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=False)
