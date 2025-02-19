import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask, request, render_template, jsonify
import os
import openai
import random

# 🔹 Lade API-Schlüssel aus Umgebungsvariablen
SPOTIFY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔹 Setze OpenAI API Key
openai.api_key = OPENAI_API_KEY

# 🔹 Initialisiere Spotify Client
spotify_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

app = Flask(__name__)

@app.route('/home')
def home():
    return "✅ Flask App is Running!"

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'GET':
        return render_template('index.html')

    # 🔹 Extrahiere Nutzereingaben
    user_genre = request.form.get('genre', '').strip().lower()
    user_mood = request.form.get('mood', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()

    if not user_genre or not user_mood or not user_artist:
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 🔹 1️⃣ Generiere Playlist-Namen mit OpenAI GPT-4o
        playlist_name = generate_playlist_name(user_mood, user_genre, user_artist)

        # 🔹 2️⃣ Finde passende Songs mit Spotify API
        search_query = f'genre:{user_genre} artist:{user_artist}'
        search_results = spotify_client.search(q=search_query, type='track', limit=15)
        track_uris = [track['uri'] for track in search_results['tracks']['items']]
        tracks_info = extract_track_info(search_results)

        # 🔹 3️⃣ Backup mit OpenAI falls keine Songs gefunden wurden
        if not track_uris:
            print("⚠️ No tracks found in Spotify. Using OpenAI for backup suggestions.")
            suggested_tracks = get_suggested_tracks(user_mood, user_genre, user_artist)
            for suggested_track in suggested_tracks:
                track_search = spotify_client.search(q=suggested_track, type='track', limit=1)
                if track_search['tracks']['items']:
                    tracks_info.append(extract_single_track(track_search['tracks']['items'][0]))

        # 🔹 4️⃣ Generiere eine Playlist-Vorschau
        playlist_preview = tracks_info[:5]  # Nur 5 Songs anzeigen

        return render_template('results.html', 
                               playlist_name=playlist_name, 
                               playlist_preview=playlist_preview,
                               mood=user_mood)

    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An error occurred. Please try again later.")

def generate_playlist_name(mood, genre, artist):
    """ 🔹 Nutzt OpenAI GPT-4o, um einen kreativen Playlist-Namen zu generieren. """
    prompt = f"Create a catchy playlist name based on:\nMood: {mood}\nGenre: {genre}\nArtist: {artist}\nName should be creative & fun."
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a creative assistant."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=20
    )
    return response["choices"][0]["message"]["content"].strip() or "Your Custom Playlist"

def get_suggested_tracks(mood, genre, artist):
    """ 🔹 Nutzt OpenAI GPT-4o, um alternative Songs vorzuschlagen. """
    prompt = f"Suggest 5 songs for a {mood} mood in {genre} genre, similar to {artist}. Only return song titles."
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=50
    )
    return response["choices"][0]["message"]["content"].split("\n")

def extract_track_info(search_results):
    """ 🔹 Extrahiert Song-Infos für die Playlist-Vorschau """
    return [{
        "title": track["name"],
        "artist": ", ".join([a["name"] for a in track["artists"]]),
        "link": track["external_urls"]["spotify"],
        "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
    } for track in search_results['tracks']['items']]

def extract_single_track(track):
    """ 🔹 Extrahiert ein einzelnes Track-Objekt """
    return {
        "title": track["name"],
        "artist": ", ".join([a["name"] for a in track["artists"]]),
        "link": track["external_urls"]["spotify"],
        "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
