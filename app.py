import os
import time
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import openai

# === Flask Setup ===
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(hours=1)

# === OpenAI Setup ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Spotify OAuth Setup (nutzt deine SPOTIPY_ Keys) ===
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-email user-top-read playlist-modify-public"
)

# === Helper für Tokens ===
def get_token():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    now = int(time.time())
    if token_info["expires_at"] - now < 60:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return token_info

# === Routes ===

@app.route("/")
def index():
    if not get_token():
        return redirect(url_for("login"))
    return render_template("index.html", session=session)

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
    return redirect(url_for("login"))

@app.route("/recommend", methods=["POST"])
def recommend():
    token_info = get_token()
    if not token_info:
        return redirect(url_for("login"))

    genre = request.form["genre"]
    artist = request.form["artist"]
    mood = request.form["mood"]

    prompt = f"Create a short playlist with 5 songs similar to {artist}, in the {genre} genre, that match a {mood} mood."

    # === GPT: Generate song suggestions ===
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        song_text = response.choices[0].message.content.strip()
        song_list = [s.strip() for s in song_text.split("\n") if s.strip()]
    except Exception as e:
        return render_template("results.html",
                               prompt=prompt,
                               songs=[],
                               playlist_url=None,
                               image_url=None,
                               error="OpenAI request failed. Please try again later.",
                               session=session)

    # === Spotify: Search + Playlist erstellen ===
    track_links, playlist_url = [], None
    try:
        sp = spotipy.Spotify(auth=token_info["access_token"])
        track_uris = []
        for song in song_list:
            result = sp.search(q=song, limit=1, type="track")
            if result["tracks"]["items"]:
                uri = result["tracks"]["items"][0]["uri"]
                track_uris.append(uri)

        if track_uris:
            user_id = sp.current_user()["id"]
            playlist = sp.user_playlist_create(user_id, f"{mood} {genre} vibes by {artist}", public=True)
            sp.playlist_add_items(playlist["id"], track_uris)
            playlist_url = playlist["external_urls"]["spotify"]

            for uri in track_uris:
                track = sp.track(uri)
                track_links.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "url": track["external_urls"]["spotify"]
                })
    except Exception as e:
        return render_template("results.html",
                               prompt=prompt,
                               songs=[],
                               playlist_url=None,
                               image_url=None,
                               error="Spotify request failed. Please log in again.",
                               session=session)

    # === DALL·E Cover ===
    image_url = None
    try:
        image_response = openai.Image.create(
            model="gpt-image-1",
            prompt=f"Album cover art for a playlist inspired by {artist}, genre {genre}, mood {mood}",
            size="512x512"
        )
        image_url = image_response["data"][0]["url"]
    except Exception as e:
        image_url = None

    # === Render ===
    return render_template("results.html",
                           prompt=prompt,
                           songs=track_links,
                           playlist_url=playlist_url,
                           image_url=image_url,
                           error=None,
                           session=session)

# === Run locally ===
if __name__ == "__main__":
    app.run(debug=True)
