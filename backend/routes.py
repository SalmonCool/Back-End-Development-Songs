from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health",methods=["GET"])
def health():
    return {"status":"OK"},200

@app.route("/count",methods=["GET"])
def count():
    if songs_list:
        count = len(songs_list)
        return {"count": str(count)},200

    return {"Message": "Internal Server Error"},500

@app.route("/song",methods=["GET"])
def songs():
    songs = db.songs.find({})
    songList = []
    for song in songs:
        songList.append(song)
    serializedList = json_util.dumps(songList)
    decodedList = json.loads(serializedList)
    return {"songs": decodedList},200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    song = db.songs.find({"id":id})
    try: 
        cursorSong = song.next()
        serializedSong = json_util.dumps(cursorSong)
        decodedSong = json.loads(serializedSong)
        return decodedSong, 200
    finally:
        return {"message": "song with id not found"},404

@app.route("/song", methods=["POST"])
def create_song():
    data = request.json
    copies = db.songs.find_one({"id":data["id"]})
    if copies is None:
        result = db.songs.insert_one(data)
        return {"inserted id": str(result.inserted_id)},201
    else:
        return {"Message": "song with id " + str(data["id"]) + " already present"},302

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    body = request.json
    song_to_update = db.songs.find_one({"id":id})
    if song_to_update is None:
        return {"message":"song not found"},404
    else:
        result = db.songs.update_one({"id": id},{"$set": body})
        print(result)
        if result.modified_count > 0:
            updated_song = db.songs.find_one({"id":id})
            serializedSong = json_util.dumps(updated_song)
            decodedSong = json.loads(serializedSong)
            return decodedSong, 201
        else:
            return {"message":"song found, but nothing updated"},200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    deleted = db.songs.delete_one({"id":id})
    if deleted.deleted_count == 0:
        return {"message":"song not found"},404
    else:
         return {},204