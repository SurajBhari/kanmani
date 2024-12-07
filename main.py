from flask import Flask, render_template, jsonify
from get_info import get_media_info, populate_yt
import json

app = Flask(__name__)

global last_song
last_song = None

@app.route("/")
def hello():
    return render_template("test.html")

@app.route("/data")
def data():
    song = get_media_info()
    global last_song
    if last_song and last_song['title'] == song['title']:
        song = last_song
    else:
        last_song = song
        song = populate_yt(song)
    return json.dumps(song, indent=4, sort_keys=True, default=str)
if __name__ == "__main__":
    app.run(port=80, debug=True)
