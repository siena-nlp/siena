import pymongo

def get_connection():
    client = pymongo.MongoClient("mongodb+srv://SIENA:_siena@siena.9cjfs.mongodb.net/SIENA?retryWrites=true&w=majority")
    db = client.DATA
    return db