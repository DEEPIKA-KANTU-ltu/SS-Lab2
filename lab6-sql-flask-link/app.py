from flask import Flask, request,redirect,render_template
import sqlite3
import os
app = Flask(__name__)

#functon to connect to the sqlite database and initialize the table
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

#Route for the registration page
@app.route('/')
def register():
    return render_template('register.html')

#route to handle user registration.
@app.route('/register', methods=['POST'])
def do_register():
    username = request.form['username']

    #Insert the new user into database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username) VALUES (?)",(username,))
    conn.commit()
    conn.close()

    return redirect('/')

#route to display registered users
@app.route('/users')
def users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('users.html',users=users)

if __name__ =='__main__':
    init_db()
    app.run(port=5000, debug=False)
