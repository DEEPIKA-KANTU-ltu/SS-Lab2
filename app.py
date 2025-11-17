from flask import Flask,request,redirect,render_template,flash,url_for,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.config["SECRET_KEY"]= "change-me-in-production"

DB_PATH = "users_data.db"

#Database init (email Unique, case_insensitive)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   first_name TEXT NOT NULL,
                   last_name TEXT NOT NULL,
                   gender Text,
                   age INTEGER,
                   work_type Text,
                   residence_type TEXT,
                   ever_married TEXT,
                   email TEXT NOT NULL,
                   password TEXT NOT NULL,
                   hypertension INTEGER,
                   heart_disease INTEGER,
                   avg_glucose_level REAL,
                   bmi REAL,
                   smoking_status TEXT,
                   stroke INTEGER,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )""")
    #case-insensitive uniqueness on email
    cursor.execute("""
                   CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_noncase
                   ON users (lower(email));""")
    conn.commit()
    conn.close()

#---------------------------------------
#Routes : Registration
#---------------------------------------
@app.route("/")
def register():
    return render_template("register.html")
 
@app.route("/register", methods=["POST"])
def do_register():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    gender = request.form.get("gender", "").strip()
    age = request.form.get("age", "").strip()
    work_type = request.form.get("work_type", "").strip()
    residence_type = request.form.get("residence_type", "").strip()
    ever_married = request.form.get("ever_married", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not (first_name and last_name and email and password):
        flash("all fields are required.")
        return redirect(url_for("register"))
    
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256" )
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #pre check duplicate
    cursor.execute("SELECT 1 FROM users WHERE lower(email) = lower(?)", (email,))
    if cursor.fetchone():
        flash("This email is already registered.Please log in instead.")
        conn.close()
        return redirect(url_for("login"))
    try:
        cursor.execute("""
                       INSERT INTO users (first_name, last_name,gender, age, work_type, residence_type, ever_married, email, password) VALUES (?,?,?,?,?,?,?,?,?)""",(first_name,last_name,gender, age, work_type, residence_type, ever_married,email,hashed_password))
        conn.commit()
        flash("Registration succesful! Please log in.")

    except sqlite3.IntegrityError:
        flash("This email is already registered.Please log in instead.")
    finally:
        conn.close()
    
    return redirect(url_for("login"))

#--------------------------------------------------------
#Rounts : Login/Logout
#--------------------------------------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    email = request.form.get("email", "").strip()
    password = request.form.get("password","")

    if not (email and password):
        flash("Please enter both email and password.")
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, first_name, last_name, email, password
                   FROM users 
                   WHERE lower(email) = lower(?)""", (email,))
    row = cursor.fetchone()
    conn.close()
 
    if not row:
        flash("Invalid email or password.")
        return redirect(url_for("login"))
    
    user_id, first_name, last_name, user_email, password_hash = row
    if not check_password_hash(password_hash, password):
        flash("Invalid email or password.")
        return redirect(url_for("login"))
    
    session["user_id"] = user_id
    session["user_email"] = user_email
    session["user_name"] = f"{first_name} {last_name}"
    flash(f"Welcome back, {first_name}!")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

#-----------------------------------------
#Authenticated page 
#-----------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to continue")
        return redirect(url_for("login"))
    return render_template('dashboard.html')
    
#List users
@app.route("/users")
def users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, first_name, last_name, gender, age, work_type, residence_type, ever_married, email, hypertension, heart_disease, avg_glucose_level, bmi, smoking_status, stroke,created_at
                   FROM users ORDER BY created_at DESC""")#FROM users ORDER BY created_at DESC""")
    rows = cursor.fetchall()
    conn.close()
    return render_template("users.html", users=rows)

#Delete user
@app.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?",(user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        flash("User not found or already deleted.")
        return redirect(url_for("users"))
    
    if user_id == session.get("user_id"):
        session.clear()
        flash("Your account was deleted. You have been logged out.")
        return redirect(url_for("login"))
    flash("User dleted.")
    return redirect(url_for("users"))

#NEW: Update user
@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    if "user_id" not in session:
        flash("Please login to continue.")
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "GET":
        cursor.execute("""
                       SELECT id, first_name, last_name, email
                       FROM users WHERE id = ?""",(user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            flash("User not found")
            return redirect(url_for("users"))
        #row = id,first_name, last_name, email
        flash("Profile updated successfully.")
        return render_template("edit_user.html", user=row)
    
    #POST : update fields
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    gender = request.form.get("gender", "").strip()
    age = request.form.get("age", "").strip()
    work_type = request.form.get("work_type", "").strip()
    residence_type = request.form.get("residence_type", "").strip()
    ever_married = request.form.get("ever_married", "").strip()
    email = request.form.get("email", "").strip()
    new_password = request.form.get("password", "")
    
    if not (first_name and last_name and email):
        conn.close()
        flash("First name, last name and email are required.")
        return redirect(url_for("edit_user", user_id=user_id))
    
    #Duplicate email check
    cursor.execute("""
                   SELECT 1 FROM users WHERE lower(email) = lower(?) AND id != ?""", (email, user_id))
    if cursor.fetchone():
        conn.close()
        flash("That email is already in use by another account.")
        return redirect(url_for("edit_user", user_id=user_id))
    
    #Build update dynamically
    if new_password.strip():
        hashed = generate_password_hash(new_password.strip(), method="pbkdf2:sha256")
        cursor.execute("""
                       UPDATE users SET first_name = ?, last_name = ?, gender=?,age=?, work_type=?, residence_type=?,ever_married=?, email = ?, password = ? WHERE id =? """, (first_name,last_name, gender,age, work_type, residence_type, ever_married,email,hashed,user_id))
    else:
        cursor.execute("""
                       UPDATE users SET first_name = ?, last_name = ?, gender=?,age=?, work_type=?, residence_type=?,ever_married=?, email = ? WHERE id =? """, (first_name,last_name,gender,age, work_type, residence_type, ever_married,email,user_id))
   
        conn.commit()
        conn.close()

        #If logged in user updates their email/name, refresh session
        if user_id == session.get("user_id"):
            session["user_email"] = email
            session["user_name"] = f"{first_name} {last_name}"

        flash("User updated succesfully.")
        return redirect(url_for("users"))
    

@app.route("/add_info", methods=["GET", "POST"])
def add_info():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        hypertension = request.form.get("hypertension")
        heart_disease = request.form.get("heart_disease")
        avg_glocose_level = request.form.get("avg_glucose_level")
        bmi = request.form.get("bmi")
        smoking_status = request.form.get("smoking_status")
        stroke = request.form.get("stroke")

        conn = sqlite3.connect(DB_PATH)
        cusror = conn.cursor()
        cusror.execute("""UPDATE users 
                       SET hypertension=?, heart_disease=?, avg_glucose_level=?, bmi=?, smoking_status=?, stroke=?
                       WHERE id=? """,
                       (hypertension, heart_disease, avg_glocose_level,bmi,smoking_status,stroke, session["user_id"]))
        conn.commit()
        conn.close()

        flash("Medical Information updated sucessfuly.")
        return redirect(url_for("dashboard"))
    return render_template("add_info.html")

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, age, gender, 
            bmi, avg_glucose_level, hypertension, heart_disease
            FROM users WHERE id=?
                   """, (session["user_id"],))
    user = cursor.fetchone()
    conn.close()
    return render_template("analyze.html", user = user)


@app.route("/history", methods=["GET", "POST"])
def history():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    return render_template("history.html")

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))
    return render_template("feedback.html")
    #Entry
   
if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=False)
         