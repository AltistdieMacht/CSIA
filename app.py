import os
from flask import Flask, request, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import openai

app = Flask(__name__)

# Hole Umgebungsvariablen
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setze OpenAI API-Key
openai.api_key = OPENAI_API_KEY

# Hole dauerhaft gültiges Zugriffstoken mit dem Refresh Token
def get_spotify_token():
    oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri="http://localhost:8888/callback",  # Dummy
    )
    oauth.refresh_access_token(SPOTIPY_REFRESH_TOKEN)
    token_info = oauth.get_cached_token()
    return token_info["access_token"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    mood = request.form["mood"]
    genre = request.form["genre"]
    artist = request.form["artist"]

    prompt = (
        f"Create a Spotify playlist with 5 songs based on the following mood and style:\n"
        f"- Mood: {mood}\n"
        f"- Genre: {genre}\n"
        f"- Similar to: {artist}\n"
        f"Return them as a numbered list: Song Title - Artist"
    )

    # Hole Vorschläge von OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )

    playlist_text = response.choices[0].message["content"]

    # Extrahiere Songs
    songs = []
    for line in playlist_text.strip().split("\n"):
        if "-" in line:
            parts = line.split("-", 1)
            title = parts[0].split(".")[-1].strip()
            artist = parts[1].strip()
            songs.append({"title": title, "artist": artist})

    # Authentifiziere Spotify
    token = get_spotify_token()
    sp = Spotify(auth=token)

    # Erstelle Playlist
    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=f"{mood} Vibes", public=False)

    track_uris = []
    for song in songs:
        query = f"{song['title']} {song['artist']}"
        result = sp.search(q=query, limit=1, type="track")
        tracks = result.get("tracks", {}).get("items", [])
        if tracks:
            track_uris.append(tracks[0]["uri"])
            song["spotify_url"] = tracks[0]["external_urls"]["spotify"]
            song["image"] = tracks[0]["album"]["images"][0]["url"]
        else:
            song["spotify_url"] = None
            song["image"] = None

    if track_uris:
        sp.playlist_add_items(playlist_id=playlist["id"], items=track_uris)

    playlist_url = playlist["external_urls"]["spotify"]

    return render_template("results.html", songs=songs, playlist_url=playlist_url)

if __name__ == "__main__":
    app.run(debug=True)
