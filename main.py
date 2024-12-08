from flask import Flask, render_template, jsonify, request
from get_info import get_media_info, populate_yt, get_current_session
import json
from asyncio import run as asyncio_run
from datetime import datetime, timedelta

app = Flask(__name__)

global last_song
last_song = None
last_endtime = timedelta(seconds=0)
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
}

@app.route("/")
def hello():
    return render_template("test.html")

@app.route("/data")
def data():
    song = get_media_info()
    global last_song
    global default_song
    if not song:
        last_song = None
        return default_song
    if last_song and last_song['title'] == song['title']:
        song = last_song
    else:
        last_song = song
        song = populate_yt(song)
    # make a copy of default_song and update the value of song on it to avoid changing the default_song
    new_song = default_song.copy()
    # if there is no thumbnail in "song" then the default thumbnail will be used
    default_thumbnail = default_song['thumbnail']
    if not song['thumbnail']:
        song['thumbnail'] = default_thumbnail
    new_song.update(song)
    return json.dumps(new_song, indent=4, sort_keys=True, default=str)


@app.route("/currentposition")
def current_position():
    global last_endtime
    session = get_current_session()
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
    if session.get_playback_info().playback_status == 5:
        now = timeline.position
    
    
    # lets clean the data a bit and only give the useful values
    useful = {}
    useful['now'] = now.seconds
    useful['start'] = 0
    useful['end'] = timeline.end_time.seconds
    useful['last_updated'] = timeline.last_updated_time
    return json.dumps(useful, indent=4, sort_keys=True, default=str)

@app.route("/lyrics")
def lyrics():
    song = get_media_info()

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
