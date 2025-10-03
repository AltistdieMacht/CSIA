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
    """Main logic for generating playlist (existing, plus save to history)."""
    genre = request.form.get("genre")
    artist = request.form.get("artist")
    mood = request.form.get("mood")

    # --- Your existing OpenAI + Spotify logic here ---
    # Example placeholders:
    custom_title = f"{mood} {genre} vibes by {artist}"
    playlist_image = "https://via.placeholder.com/300"
    songs = [
        {"title": "Song 1", "artist": artist, "image": None, "spotify_url": None},
        {"title": "Song 2", "artist": artist, "image": None, "spotify_url": None}
    ]
    playlist_url = "https://open.spotify.com/playlist/example"

    # --- NEW: Save to history if user is logged in ---
    try:
        token_info = get_token_info()
        if token_info:
            sp_u = spotipy.Spotify(auth=token_info["access_token"])
            me = sp_u.current_user()
            prompt_text = f"{genre}, {artist}, {mood}"
            conn = sqlite3.connect("app.db")
            c = conn.cursor()
            c.execute("INSERT INTO history (spotify_id, prompt, playlist_url) VALUES (?, ?, ?)",
                      (me["id"], prompt_text.strip(", "), playlist_url))
            conn.commit()
            conn.close()
    except Exception:
        pass

    return render_template(
        "results.html",
        custom_title=custom_title,
        playlist_image=playlist_image,
        songs=songs,
        playlist_url=playlist_url
    )

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
