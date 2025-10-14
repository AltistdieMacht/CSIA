import os
import time
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import openai

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dev")
app.permanent_session_lifetime = timedelta(hours=2)

openai.api_key = os.getenv("OPENAI_API_KEY")

# Spotify OAuth setup
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-email playlist-modify-public playlist-modify-private"
)

def get_token():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    now = int(time.time())
    if token_info["expires_at"] - now < 60:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return token_info

@app.route("/")
def index():
    token_info = get_token()
    if not token_info:
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

    genre = request.form.get("genre", "")
    artist = request.form.get("artist", "")
    mood = request.form.get("mood", "")

    # GPT – Generate playlist title & songs (improved version)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"Create a playlist title and a list of exactly 5 songs that match the artist '{artist}', "
                    f"in the '{genre}' genre, and fit a '{mood}' mood. "
                    f"The title should be short, creative, and sound like a real Spotify playlist name "
                    f"(e.g., 'Midnight Reflections' or 'Summer Drive'). "
                    f"If the artist is older (for example, classic rock or 20th-century artists), "
                    f"you may include both modern and older songs that align with their style. "
                    f"For modern artists, prioritize songs released after 2010. "
                    f"Format the response as:\n\n"
                    f"Title: <playlist title>\n"
                    f"1. <song> - <artist>\n"
                    f"2. <song> - <artist>\n"
                    f"3. <song> - <artist>\n"
                    f"4. <song> - <artist>\n"
                    f"5. <song> - <artist>\n"
                )
            }],
            max_tokens=300,
            temperature=0.8
        )

        text = response.choices[0].message.content.strip()

        # Extract playlist title
        title_line = next((ln for ln in text.split("\n") if ln.lower().startswith("title:")), None)
        playlist_title = title_line.split(":", 1)[1].strip() if title_line else "AI-Generated Playlist"

        # Extract songs
        song_lines = [ln.split(".", 1)[-1].strip() for ln in text.split("\n") if "-" in ln]

    except Exception:
        playlist_title = "AI-Generated Playlist"
        song_lines = []

    sp = Spotify(auth=token_info["access_token"])
    songs, uris = [], []

    # Search each song on Spotify
    for line in song_lines[:5]:
        try:
            name, artist_name = [x.strip() for x in line.split("-", 1)]
            res = sp.search(q=f"track:{name} artist:{artist_name}", type="track", limit=1)
            items = res.get("tracks", {}).get("items", [])
            if not items:
                continue
            track = items[0]
            songs.append({
                "title": track["name"],
                "artist": track["artists"][0]["name"],
                "image": track["album"]["images"][1]["url"] if track["album"]["images"] else None,
                "spotify_url": track["external_urls"]["spotify"]
            })
            uris.append(track["uri"])
        except Exception:
            continue

    # Create Spotify playlist
    playlist_url = None
    if uris:
        user_id = sp.current_user()["id"]
        pl = sp.user_playlist_create(user=user_id, name=playlist_title, public=True)
        sp.playlist_add_items(pl["id"], uris)
        playlist_url = pl["external_urls"]["spotify"]

    # DALL·E – Generate cover
    playlist_image = None
    try:
        image = openai.Image.create(
            model="dall-e-3",
            prompt=f"Modern Spotify playlist cover for '{playlist_title}', {genre} genre, {mood} vibe.",
            size="1024x1024"
        )
        playlist_image = image["data"][0]["url"]
    except Exception:
        playlist_image = None

    return render_template(
        "results.html",
        playlist_title=playlist_title,
        songs=songs,
        playlist_url=playlist_url,
        playlist_image=playlist_image
    )

if __name__ == "__main__":
    app.run(debug=True)
