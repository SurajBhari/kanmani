import requests
from bs4 import BeautifulSoup
import random
import string
from urllib.parse import urlencode
import json

def genius(artist, title):
    # Genius API
    url = "https://genius.com/api/search/song"
    search_url = f"{url}?q={artist} {title}&per_page=1"
    response = requests.get(search_url)
    data = response.json()
    try:
        song = data["response"]["sections"][0]["hits"][0]["result"]
    except (KeyError, IndexError):
        return {}
    song_url = song["url"]
    print(song_url)
    soup = BeautifulSoup(requests.get(song_url).text, "html.parser")
    # write the soup html to a file for temp
    with open("soup.html", "w", encoding="utf-8") as file:
        file.write(soup.prettify())
    # all div with data-lyrics-container="true" are the lyrics
    lyrics = []
    for div in soup.find_all("div", {"data-lyrics-container": "true"}):
        for element in div.contents:
            if element.name == 'br':
                lyrics.append("\n")  # Add a blank line for <br/> without text
            elif isinstance(element, str):
                lyrics.append(element.strip())
            elif element.name in ['b', 'i', 'u']:  # Handle text inside tags like <b>
                lyrics.append(element.get_text(strip=True))
    # remove any empty lines
    lyrics = "".join([l for l in lyrics if l]).split("\n")
    return {"provider": "Genius", "lyrics": lyrics, "synchronized": False}

def musixmatch(artist: str, title: str, token:str) -> dict:
    base_url = "https://apic-desktop.musixmatch.com/ws/1.1/"
    if not token:
        return {"error": "Unable to retrieve token"}
    
    params = {
        "app_id": "web-desktop-app-v1.0",
        "usertoken": token,
        "format": "json",
        "namespace": "lyrics_richsynched",
        "optional_calls": "track.richsync",
        "subtitle_format": "mxm",
        "q_artist": artist,
        "q_track": title,
    }
    
    try:
        response = requests.get(f"{base_url}macro.subtitles.get?{urlencode(params)}")
        response.raise_for_status()
        result = response.json()
        # write this to json file temporarily
        with open("musixmatch.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(result, indent=4))

        body = result.get("message", {}).get("body", {})
        macro_calls = body.get("macro_calls", {})
        try:
            subtitle = macro_calls.get("track.subtitles.get", {}).get("message", {}).get("body", {}).get("subtitle_list", [{}])[0].get("subtitle", {})
        except (AttributeError, IndexError):
            subtitle = None
        if subtitle:
            subtitle_body = subtitle.get("subtitle_body", [])
            if not subtitle_body:
                return {}
            subtitle_body = json.loads(subtitle_body)
            lines = [
                {"text": v["text"], "time": v["time"]["total"]}
                for v in subtitle_body
            ]
            return {
                "provider": "Musixmatch",
                "lyrics": lines,
                "copyright": subtitle.get("lyrics_copyright", "").replace("\n", " • ").strip(),
                "synchronized": True
            }
        try:
            lyrics = macro_calls.get("track.lyrics.get", {}).get("message", {}).get("body", {}).get("lyrics", {})
        except (AttributeError, IndexError):
            lyrics = None
        if lyrics:
            return {
                "provider": "Musixmatch",
                "lyrics": lyrics.get("lyrics_body", "").strip(),
                "copyright": lyrics.get("lyrics_copyright", "").replace("\n", " • ").strip(),
                "synchronized": False
            }
        
        
    except requests.RequestException as e:
        print("Failed to fetch lyrics from Musixmatch:", e)
        return {}
    
    return {}
