'''import sqlalchemy
import flask_sqlalchemy

print(sqlalchemy.__version__)
print(flask_sqlalchemy.__version__)
'''
import sqlite3
import os
folder_path= r"D:\SS"

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

db_path = os.path.join(folder_path,'currency.db')

conn = sqlite3.connect(db_path)

cursor = conn.cursor()
cursor.execute("SELECT * FROM currency;")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
