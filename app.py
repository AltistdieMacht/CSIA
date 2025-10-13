import os
import time
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import openai

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(hours=2)

openai.api_key = os.getenv("OPENAI_API_KEY")

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-email user-top-read playlist-modify-public playlist-modify-private"
)

def get_token():
    token_info = session.get("token_info")
    if not token_info:
        return None
    now = int(time.time())
    if token_info["expires_at"] - now < 60:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return token_info

@app.route("/")
def index():
    if not get_token():
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login")
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return render_template("login.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    token_info = get_token()
    if not token_info:
        return redirect(url_for("login"))

    genre = (request.form.get("genre") or "").strip()
    artist = (request.form.get("artist") or "").strip()
    mood = (request.form.get("mood") or "").strip()
    custom_title = f"Create a short playlist with 5 songs similar to {artist}, in the {genre} genre, that match a {mood} mood."

    try:
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"List 5 song titles with artist names that match this: {custom_title}. Output one per line as 'Title - Artist'."}],
            max_tokens=140,
            temperature=0.7
        )
        raw = chat.choices[0].message.content.strip()
        lines = [ln.strip("-• ").strip() for ln in raw.split("\n") if ln.strip()]
    except Exception:
        return render_template("results.html", custom_title=custom_title, playlist_image=None, songs=[], playlist_url="#")

    sp = spotipy.Spotify(auth=token_info["access_token"])

    track_uris = []
    songs = []
    for line in lines[:5]:
        parts = [p.strip() for p in line.split(" - ", 1)]
        query = line
        if len(parts) == 2:
            query = f'track:"{parts[0]}" artist:"{parts[1]}"'
        res = sp.search(q=query, type="track", limit=1)
        items = res.get("tracks", {}).get("items", [])
        if not items:
            continue
        t = items[0]
        track_uris.append(t["uri"])
        songs.append({
            "title": t["name"],
            "artist": t["artists"][0]["name"],
            "image": (t["album"]["images"][1]["url"] if t["album"]["images"] else None),
            "spotify_url": t["external_urls"]["spotify"]
        })

    playlist_url = "#"
    if track_uris:
        me = sp.current_user()["id"]
        pl = sp.user_playlist_create(user=me, name=f"{mood} {genre} vibes by {artist}".strip(), public=True)
        sp.playlist_add_items(pl["id"], track_uris)
        playlist_url = pl["external_urls"]["spotify"]

    playlist_image = None
    try:
        img = openai.Image.create(
            model="dall-e-3",
            prompt=f"Album cover art for a playlist inspired by {artist}, {genre} genre, {mood} mood. Minimal, modern, high contrast.",
            size="1024x1024",
            n=1
        )
        playlist_image = img["data"][0]["url"]
    except Exception:
        playlist_image = None

    return render_template(
        "results.html",
        custom_title=custom_title,
        playlist_image=playlist_image,
        songs=songs,
        playlist_url=playlist_url
    )

if __name__ == "__main__":
    app.run(debug=True)
