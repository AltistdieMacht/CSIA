import os
import base64
from flask import Flask, request, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import openai

app = Flask(__name__)

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def get_spotify_token():
    oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri="http://localhost:8888/callback"
    )
    oauth.refresh_access_token(SPOTIPY_REFRESH_TOKEN)
    return oauth.get_cached_token()["access_token"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    mood = request.form.get("mood")
    genre = request.form.get("genre")
    artist = request.form.get("artist")

    prompt = (
        f"Create a Spotify playlist with 5 songs based on the following mood and style:\n"
        f"- Mood: {mood}\n"
        f"- Genre: {genre}\n"
        f"- Similar to: {artist}\n"
        f"Return them as a numbered list: Song Title - Artist"
    )

    # 🎧 Musikvorschläge holen
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a music expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=500
    )
    playlist_text = response.choices[0].message["content"]

    # Titel generieren
    title_prompt = f"Generate a catchy playlist title for a playlist that is {mood}, in the {genre} genre, and inspired by {artist}. Only return the title."
    title_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": title_prompt}],
        temperature=0.7,
        max_tokens=20
    )
    custom_title = title_response.choices[0].message["content"].strip()

    # Songs extrahieren
    songs = []
    for line in playlist_text.strip().split("\n"):
        if "-" in line:
            parts = line.split("-", 1)
            title = parts[0].split(".")[-1].strip()
            artist_name = parts[1].strip()
            songs.append({"title": title, "artist": artist_name})

    # Spotify Auth
    token = get_spotify_token()
    sp = Spotify(auth=token)

    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=custom_title, public=True)

    track_uris = []
    for song in songs:
        query = f"{song['title']} {song['artist']}"
        result = sp.search(q=query, limit=1, type="track")
        tracks = result.get("tracks", {}).get("items", [])
        if tracks:
            track = tracks[0]
            track_uris.append(track["uri"])
            song["spotify_url"] = track["external_urls"]["spotify"]
            song["image"] = track["album"]["images"][0]["url"]
        else:
            song["spotify_url"] = None
            song["image"] = None

    if track_uris:
        sp.playlist_add_items(playlist_id=playlist["id"], items=track_uris)

    playlist_url = playlist["external_urls"]["spotify"]

    # 🎨 DALL·E 3 Image
    image_prompt = f"Abstract album cover artwork representing a {mood} mood in {genre} genre, inspired by {artist}. Vibrant, emotional, and high-resolution."
    image_response = openai.Image.create(
        model="dall-e-3",
        prompt=image_prompt,
        n=1,
        size="1024x1024",
        response_format="b64_json"
    )
    image_b64 = image_response["data"][0]["b64_json"]
    cover_url = f"data:image/png;base64,{image_b64}"

    return render_template("results.html", songs=songs, playlist_url=playlist_url, playlist_image=cover_url, custom_title=custom_title)

if __name__ == "__main__":
    app.run(debug=True)
    