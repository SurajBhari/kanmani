from flask import Flask, render_template, jsonify, request, send_file
from get_info import get_media_info, populate_yt, get_current_session
import json
from asyncio import run as asyncio_run
from datetime import datetime, timedelta
import syncedlyrics
import random
import string
import requests
from urllib.parse import urlencode
import os
import pylrc
import re


app = Flask(__name__)

global last_song
last_song = None
global last_lyrics
last_lyrics = None
last_endtime = 0
default_song = {
    "artist": "Unknown",
    "title": "Unknown",
    "genres": [],
    "playback_status": "Unknown",
    "playback_type": "Unknown",
    "end_time": "Unknown",
    "last_updated": "Unknown",
    "max_seek": "Unknown",
    "min_seek": "Unknown",
    "position": "Unknown",
    "start_time": "Unknown",
    "thumbnail": "https://img.freepik.com/premium-photo/white-cd-disk_700248-115.jpg?semt=ais_hybrid",
    "link": "Unknown",
    "id": "Unknown",
    "artists": [],
    "album":""
}

def write_config(config: dict): 
    with open("config.json", "w") as file:
        file.write(json.dumps(config, indent=4))
    return True

try:
    file = open("config.json.sample", "r")
    try:
        default_config = json.load(file)
    except json.JSONDecodeError:
        default_config = {}
    file.close()
except FileNotFoundError:
    default_config = {}

try:
    file = open("config.json", "r")
    try:
        config = json.load(file)
    except json.JSONDecodeError:
        print("Corrupted config file, using default config")
        config = default_config
    file.close()
except FileNotFoundError:
    print("No config file found, using default config")
    # copy the default config to the config file
    with open("config.json", "w") as file:
        file.write(json.dumps(default_config, indent=4))
    config = default_config
    if not default_config:
        exit("No default config found, exiting")

known_songs_lyrics = {} # "artist-title": lyrics


@app.route("/")
def hello():
    return render_template("main.html")

@app.route("/obs")
def obs():
    return render_template("obs.html")
@app.route("/data")
def data():
    song = get_media_info()
    global last_song
    global default_song
    if not song:
        last_song = None
        return default_song
    song['artist'], song['title'] = clean_up(song['artist'], song['title'])
    if last_song and last_song['title'] == song['title']:
        song = last_song
    else:
        last_song = song
        song = populate_yt(song)
    # make a copy of default_song and update the value of song on it to avoid changing the default_song
    new_song = default_song.copy()
    # if there is no thumbnail in "song" then the default thumbnail will be used
    default_thumbnail = default_song['thumbnail']
    if not song.get('thumbnail', None):
        song['thumbnail'] = default_thumbnail
    new_song.update(song)
    return json.dumps(new_song, indent=4, sort_keys=True, default=str)

def beautify(seconds):
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    hour = int(hour)
    minutes = int(minutes)
    seconds = int(seconds)

    if hour:
        return f"{hour}:{minutes}:{seconds}"
    if minutes:
        return f"{minutes}:{seconds}"
    return f"{seconds}"


@app.route("/currentposition")
def current_position():
    global last_endtime
    session = get_current_session()
    if not session:
        return {}
    timeline = session.get_timeline_properties()
    # try to make sense here 
    current_time = datetime.now().timestamp()
    last_updated = timeline.last_updated_time.timestamp()
    time_since_last_updated = current_time - last_updated
    # we were at "position" at "last_updated_time"
    # we are now at "position" + "time_since_last_updated"
    now = timeline.position + timedelta(seconds=time_since_last_updated)
    # if we are paused then the position is litreally 'position'
    # if last_endtime is not same as timeline.end_time then we have a new song and we substract 
    if not last_endtime:
        last_endtime = timeline.end_time
    if last_endtime != timeline.end_time:
        now = timeline.position
        last_endtime = timeline.end_time
    playing = True
    if session.get_playback_info().playback_status == 5:
        playing = False
        now = timeline.position
    
    
    # lets clean the data a bit and only give the useful values
    useful = {}
    useful['now'] = now.seconds
    useful['start'] = 0
    useful['end'] = timeline.end_time.seconds
    useful['last_updated'] = timeline.last_updated_time
    useful['playing'] = playing
    return json.dumps(useful, indent=4, sort_keys=True, default=str)

def clean_up(artist, title):
    if artist.lower() in title.lower(): # Abdul Hannan - Haaray         ---- title
        title = title.replace(artist, "").strip()
        title= title.replace("-","").strip()
        title = title.replace("–", "").strip() # FUCK YOU https://www.youtube.com/watch?v=R-sh3kfdHQ4
    # remove the extra "-" from the title 
    if "topic" in artist.lower():
        artist = artist.replace("Topic", "").strip()
    separators = ["\\|", "-", ":", "\\(", "\\[", "lyric", "lyrics", "lyrical", "song", "full", "title", "video"]
    for sep in separators:
        if sep.replace("\\", "") in title.lower():
            title = re.split(sep, title, flags=re.IGNORECASE)
            title = title[0].strip()
    return artist, title
@app.route("/lastlyrics")
def ll():
    global last_lyrics
    if not last_lyrics:
        last_lyrics = {"lyrics": [], "synchronized": False}
    return last_lyrics

@app.route("/favicon.ico")
def favicon():
    return send_file("./static/favicon.ico")

@app.route("/lyrics")
def _lyrics():
    global last_lyrics

    artist = request.args.get("artist", "Unknown")
    title = request.args.get("title", "Unknown")
    artist, title = clean_up(artist, title)
    if f"{artist}-{title}" in known_songs_lyrics:
        return jsonify(known_songs_lyrics[f"{artist}-{title}"])  
    print(f"Searching for {title} {artist}")  
    lrc = syncedlyrics.search(f"{title} {artist}")
    with open("lyrics.txt", "w", encoding="utf-8") as file:
        file.write(lrc) if lrc else file.write("No lyrics found")
    if not lrc:
        last_lyrics = {"lyrics": [], "synchronized": False}
        known_songs_lyrics[f"{artist}-{title}"] = last_lyrics
        return known_songs_lyrics[f"{artist}-{title}"]
    subs = pylrc.parse(lrc)
    lyrics = {"lyrics":[]}
    for line in subs:
        text = line.text
        time = line.time
        lyrics["lyrics"].append({"text": text.strip(), "time": time})
    lyrics["synchronized"] = True
    known_songs_lyrics[f"{artist}-{title}"] = lyrics
    last_lyrics = lyrics
    return lyrics

@app.route("/play")
def play():
    try:
        return str(get_current_session().try_play_async().get_results())
    except OSError:
        return "False"
    
@app.route("/pause")
def pause():
    try:
        return str(get_current_session().try_pause_async().get_results())
    except OSError:
        return "False"

@app.route("/next")
def next():
    try:
        return str(get_current_session().try_skip_next_async().get_results())
    except OSError:
        return "False"

@app.route("/prev")
def prev():
    try:
        return str(get_current_session().try_skip_previous_async().get_results())
    except OSError:
        return "False"

@app.route("/playpause")
def playpause():
    session = get_current_session()
    try:
        str(session.try_toggle_play_pause_async().get_results())
    except OSError:
        pass
    playing = session.get_playback_info().playback_status != 4
    return "True" if playing else "False"


if __name__ == "__main__":
    app.run(port=80, debug=True)
