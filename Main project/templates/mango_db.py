from flask import Flask, render_template, request, redirect,url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd

app= Flask(__name__)

#MongoDB connection
client = MongoClient('mongodb+srv://kantudeepika2005:Deepika20051$@lab7.uukbesg.mongodb.net/')
db = client['World']
collection = db['cities']

#home page
@app.route('/')
def index():
    #get all documents
    docs = list(collection.find())

    #convert objectId to string so html can use it.
    for d in docs:
        d['_id'] = str(d['_id'])

    #Nice preview table useing pandas, first 10 rows
    if docs:
        df = pd.DataFrame(docs).head(10)
        preview_table_html = df.to_html(classes='data', index=False)
    else:
        preview_table_html= "<p>No data yet.</p>"

    return render_template('dashboard.html', records=docs, preview_table=preview_table_html)

#CREATE (form page and submit)
@app.route('/add', methods = ['POST'])
def add_form():
    return render_template('add.html')

@app.route('/add', methods = ['POST'])
def add_record():
    # pull fields from ,form>
    name= request.form.ger('name')
    country = request.form.get('country')
    population = request.form.get('population')

    # build a new document
    new_doc ={
        "name" : name,
        "country" : country,
        "population" : int(population) if population else None

    }
    #insert into mongoDB
    collection.insert_one(new_doc)
    return redirect(url_for('dashboard.html'))

#UPDATE (edict + submit)
#show edit form with existing data
@app.route('/edit/<id>', methods = ['GET'])
def edit_form(id):
    doc = collection.find_one({"_id": ObjectId(id)})
    if not doc:
        #if not found go home
        return redirect(url_for('dashboard.html'))
    doc['_id'] = str(doc['_id'])
    return render_template('edit.html', record=doc)
@app.route ('/edit/<id>', methods=['POST'])
def update_record(id):
    name = request.form.get('name')
    country = request.form.get('country')
    population = request.form.get('population')
    update_doc = {
        "name" : name,
        "country" : country,
        "population" : int(population) if population else None

    }
    collection.update_one(
        {"_id": ObjectId(id)},
        {"$set" : update_doc}
    )
    return redirect(url_for('dashboard.html'))

#DELETE
@app.route('/delete/<id>', methods=['POST'])
def dlete_record(id):
    collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('dashboard.html'))

#Run app
if __name__ == "__main__":
    app.run(debug=True)


