import os
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, render_template
from dotenv import load_dotenv
import requests
from PIL import Image
from io import BytesIO
import base64

# Load environment variables
load_dotenv()

# Ensure Render-style env variables are mapped for Spotipy
if os.getenv("CLIENT_ID") and not os.getenv("SPOTIPY_CLIENT_ID"):
    os.environ["SPOTIPY_CLIENT_ID"] = os.getenv("CLIENT_ID")
if os.getenv("CLIENT_SECRET") and not os.getenv("SPOTIPY_CLIENT_SECRET"):
    os.environ["SPOTIPY_CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")

openai.api_key = os.getenv("OPENAI_API_KEY")

# Spotify authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="playlist-modify-public ugc-image-upload",
    username=os.getenv("SPOTIFY_USERNAME")
))

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    genre = request.form["genre"]
    artist = request.form["artist"]
    mood = request.form["mood"]

    # Step 1: Use GPT-4o to generate playlist metadata
    chat_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a creative music expert and playlist curator."},
            {"role": "user", "content": f"Create a playlist with 5 songs based on the mood '{mood}', the genre '{genre}', and inspired by the artist '{artist}'. Give me:\n1. Playlist title\n2. Short description\n3. 5 song titles with artist names\n4. A short DALL\u00b7E prompt to generate a cover image"}
        ]
    )

    result_text = chat_response.choices[0].message.content.strip().split("\n")
    playlist_name = result_text[0].strip()
    playlist_description = result_text[1].strip()
    songs = [line.strip() for line in result_text[2:7]]
    dalle_prompt = result_text[7] if len(result_text) > 7 else f"Album cover for a {mood} {genre} playlist"

    # Step 2: Generate cover image with DALL\u00b7E 3
    image_response = openai.Image.create(
        model="dall-e-3",
        prompt=dalle_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    image_url = image_response['data'][0]['url']

    # Step 3: Create Spotify Playlist
    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True, description=playlist_description)
    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]

    # Step 4: Search and add tracks
    track_uris = []
    for song in songs:
        try:
            res = sp.search(q=song, limit=1, type="track")
            track_uri = res["tracks"]["items"][0]["uri"]
            track_uris.append(track_uri)
        except:
            continue

    if track_uris:
        sp.playlist_add_items(playlist_id, track_uris)

    # Step 5: Upload playlist cover image
    try:
        img_data = requests.get(image_url).content
        img = Image.open(BytesIO(img_data)).convert("RGB").resize((640, 640))
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        sp.playlist_upload_cover_image(playlist_id, img_base64)
    except Exception as e:
        print(f"Failed to upload image: {e}")

    preview_songs = [song for song in songs if song]

    return render_template("results.html",
                           playlist_name=playlist_name,
                           playlist_description=playlist_description,
                           preview_songs=preview_songs,
                           playlist_link=playlist_url,
                           playlist_cover=image_url)

if __name__ == "__main__":
    app.run(debug=True)
