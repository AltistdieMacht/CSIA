import os
import time
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# -----------------------------
# Flask Setup
# -----------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# -----------------------------
# Spotify OAuth Setup
# -----------------------------
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="user-read-email user-read-private user-top-read playlist-modify-private"
)

# -----------------------------
# Database Setup (SQLite)
# -----------------------------
def init_db():
    """Create tables for users and history if they don't exist yet."""
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        spotify_id TEXT PRIMARY KEY,
        display_name TEXT,
        refresh_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spotify_id TEXT,
        prompt TEXT,
        playlist_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Helper: Refresh Token if Needed
# -----------------------------
def get_token_info():
    """Return a valid token_info from session (refresh if expired)."""
    token_info = session.get("token_info")
    if not token_info:
        return None
    now = int(time.time())
    if token_info.get("expires_at", 0) - now < 60:
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            session["token_info"] = token_info
        except Exception:
            session.pop("token_info", None)
            return None
    return token_info

# -----------------------------
# Routes: Spotify Auth
# -----------------------------
@app.route("/login")
def login():
    """Start Spotify login process."""
    return redirect(sp_oauth.get_authorize_url())

@app.route("/callback")
def callback():
    """Spotify redirects here after login with a code."""
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    sp = spotipy.Spotify(auth=token_info["access_token"])
    me = sp.current_user()

    # Save or update user in DB
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (spotify_id, display_name, refresh_token) VALUES (?, ?, ?)",
        (me["id"], me.get("display_name", me["id"]), token_info.get("refresh_token"))
    )
    conn.commit()
    conn.close()

    return redirect(url_for("profile"))

@app.route("/logout")
def logout():
    """Log out user (clear session)."""
    session.pop("token_info", None)
    return redirect(url_for("index"))

# -----------------------------
# Routes: Profile & History
# -----------------------------
@app.route("/profile")
def profile():
    """Show logged-in user's Spotify profile and top artists."""
    token_info = get_token_info()
    if not token_info:
        return redirect(url_for("login"))

    sp = spotipy.Spotify(auth=token_info["access_token"])
    me = sp.current_user()

    top_artists = []
    try:
        top_artists = sp.current_user_top_artists(limit=5).get("items", [])
    except Exception:
        top_artists = []

    return render_template("profile.html", user=me, top_artists=top_artists)

@app.route("/history")
def history():
    """Show saved recommendations for the logged-in user."""
    token_info = get_token_info()
    if not token_info:
        return redirect(url_for("login"))

    sp = spotipy.Spotify(auth=token_info["access_token"])
    me = sp.current_user()

    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT prompt, playlist_url, created_at FROM history WHERE spotify_id = ? ORDER BY created_at DESC", (me["id"],))
    rows = c.fetchall()
    conn.close()

    return render_template("history.html", rows=rows)

# -----------------------------
# Original Home Page
# -----------------------------
@app.route("/")
def index():
    """Landing page with form (unchanged)."""
    return render_template("index.html")

# -----------------------------
# Recommend Route (existing)
# -----------------------------
@app.route("/recommend", methods=["POST"])
def recommend():
    genre = request.form["genre"]
    artist = request.form["artist"]
    mood = request.form["mood"]

    prompt = f"Create a short playlist with 5 songs similar to {artist}, in the {genre} genre, that match a {mood} mood."

    # === GPT: Generate song suggestions ===
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    song_text = response.choices[0].message.content.strip()
    song_list = song_text.split("\n")

    # === Spotify API: Get track URIs ===
    token_info = session.get("token_info")
    sp = spotipy.Spotify(auth=token_info["access_token"]) if token_info else None

    track_uris = []
    if sp:
        for song in song_list:
            result = sp.search(q=song, limit=1, type="track")
            if result["tracks"]["items"]:
                track_uris.append(result["tracks"]["items"][0]["uri"])

        # Playlist erstellen
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(user_id, f"{mood} {genre} vibes by {artist}", public=True)
        sp.playlist_add_items(playlist["id"], track_uris)

        playlist_url = playlist["external_urls"]["spotify"]

        # Song-Details inkl. Spotify-Links
        track_links = []
        for uri in track_uris:
            track = sp.track(uri)
            track_links.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "url": track["external_urls"]["spotify"]
            })
    else:
        # Falls kein Spotify-Login vorhanden → nur Text anzeigen
        track_links = [{"name": s, "artist": "Unknown", "url": "#"} for s in song_list]
        playlist_url = None

    # === DALL·E: Generate playlist cover ===
    image_response = client.images.generate(
        model="gpt-image-1",
        prompt=f"Album cover art for a playlist inspired by {artist}, genre {genre}, mood {mood}",
        size="512x512"
    )
    image_url = image_response.data[0].url

    # === Save history (falls Spotify eingeloggt) ===
    try:
        save_history(prompt, ", ".join([t["name"] for t in track_links]))
    except:
        pass

    # === Render Template ===
    return render_template(
        "results.html",
        prompt=prompt,
        songs=track_links,
        playlist_url=playlist_url,
        image_url=image_url,
        session=session
    )

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
