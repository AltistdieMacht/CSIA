import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask, request, render_template, jsonify
import random
import os

print("🔍 TEST: Spotify CLIENT_ID =", os.getenv("CLIENT_ID"))
print("🔍 TEST: Spotify CLIENT_SECRET =", os.getenv("CLIENT_SECRET"))

app = Flask(__name__)

# Spotify API Setup
SPOTIFY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")

spotify_client = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
    )
)

@app.route('/')
def home():
    return "✅ Flask App is Running on Render!"

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    print(f"🔹 Incoming request: {request.method}")

    if request.method == 'GET':
        return render_template('index.html')

    print(f"🔹 Form Data Received: {request.form}")

    user_genre = request.form.get('genre', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()
    user_mood = request.form.get('mood', '').strip()

    print(f"🔹 Extracted Data - Genre: {user_genre}, Artist: {user_artist}, Mood: {user_mood}")

    if not user_genre or not user_artist or not user_mood:
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 1️⃣ Suche nach Artist-ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']

        # 2️⃣ Ähnliche Künstler basierend auf Genre
        related_artists = spotify_client.search(q=user_genre, type='artist', limit=5)
        similar_artists = [artist['id'] for artist in related_artists['artists']['items']]

        recommended_tracks = []
        for artist in similar_artists:
            top_tracks = spotify_client.artist_top_tracks(artist)
            if not top_tracks['tracks']:
                continue

            for track in top_tracks['tracks'][:2]:  # Maximal 2 Songs pro Künstler
                # 🎯 **Genre-Filterung verbessern**
                if user_genre.lower() not in [g.lower() for g in artist_search['artists']['items'][0].get('genres', [])]:
                    continue  # Falls das Genre nicht passt → Überspringen
                
                recommended_tracks.append({
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "link": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                    "popularity": track['popularity']  # ✅ Popularity Score hinzufügen
                })

        if not recommended_tracks:
            return render_template('index.html', error="No recommendations found. Try different inputs.")

        # 🎯 **Songs nach Popularity Score sortieren**
        recommended_tracks = sorted(recommended_tracks, key=lambda x: x["popularity"], reverse=True)

        # 🎯 **Songs mischen, damit nicht immer die gleichen oben sind**
        random.shuffle(recommended_tracks)

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
