import sqlite3
def connect_db():
    '''connect to sqlite database and retrn connection & cursor'''
    conn = sqlite3.connect("example1.db")
    cursor = conn.cursor()
    return conn, cursor

def create_table():
    '''create a new user into the table.'''
    conn,cursor = connect_db()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER NOT NULL);''')
    conn.commit()
    conn.close()

def insert_user(name,age):
    '''insert new user into table'''
    conn, cursor= connect_db()
    cursor.execute("INSERT INTO users (name,age) VALUES (?,?)",(name,age))
    conn.commit()
    conn.close()

def view_users():
    '''fetch user data'''
    conn, cursor=connect_db()
    cursor.execute("SELECT * FROM users")
    rows= cursor.fetchall()
    conn.close()

    print("\n--- Users in Database ---")
    if rows:
        for row in rows:
            print(f"ID: {row[0]},Name: {row[1]},Age: {row[2]}")
    else:
        print("No records found.")

    #page 15 in labe work.
def update_user(user_id, new_age):
    '''Update a users age by ID.'''
    conn,cursor=connect_db()
    cursor.execute("UPDATE users SET age = ? WHERE id = ?",(new_age,user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    '''Delete a user by ID'''
    conn,cursor=connect_db()
    cursor.execute("DELETE FROME users WHERE id = ?",(user_id))
    conn.commit()
    conn.close()

def search_users(keyword):
    ''' Search user by name or ID.
    Allow partial name matches.'''
    conn,cursor=connect_db()

    if str(keyword).isdigit():
        cursor.execute("SELECT * FROM users WHERE id = ?",(int(keyword),))
    else:
       cursor.execute("SELECT * FROM users WHERE name LIKE ?",(f"%{keyword}%",))
    
    results = cursor.fetchall()
    conn.close()

    print(f"\n--- Search Results for '{keyword}' ---")
    if results:
        for row in results:
            print(f"ID: {row[0]}, Name: {row[1]}, Age:{row[2]}")
    else:
        print("No match found.") 
# ---------------------------------------
#Main prigramm    
create_table()

#sample data
insert_user("Deepika", 20)
insert_user("Bob",35)
insert_user("Charls",25)

view_users()

print("\nSearching for 'Bob':")
search_users("Bob")

print("\nSearching for ID '3':")
search_users("3")

print("\nSearching for 'Dee': (partial match)")
search_users("Dee")