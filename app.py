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
def recommend_taste_based():
    print(f"🔹 Incoming request: {request.method}")

    if request.method == 'GET':
        print("✅ GET request received. Returning index.html")
        return render_template('index.html')

    print(f"🔹 Form Data Received: {request.form}")

    user_genre = request.form.get('genre', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()
    user_mood = request.form.get('mood', '').strip()

    print(f"🔹 Extracted Data - Genre: {user_genre}, Artist: {user_artist}, Mood: {user_mood}")

    if not user_genre or not user_artist or not user_mood:
        print("⚠️ ERROR: Missing form fields! Returning index.html")
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # **1️⃣ Search for Artist**
        print(f"🔹 Searching for artist: {user_artist}")
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)

        if not artist_search['artists']['items']:
            print(f"⚠️ ERROR: No artist found for '{user_artist}'")
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']
        artist_genres = artist_search['artists']['items'][0].get('genres', [])
        print(f"✅ Artist Found: {artist_id}, Genres: {artist_genres}")

        # **2️⃣ Search for Tracks**
        print(f"🔹 Searching for tracks in genre: {user_genre}")
        genre_query = f"genre:{user_genre}" if user_genre else ""
        genre_tracks = spotify_client.search(q=genre_query, type='track', limit=10)

        if 'tracks' not in genre_tracks or 'items' not in genre_tracks['tracks'] or not genre_tracks['tracks']['items']:
            print("⚠️ ERROR: No tracks found from search.")
            return render_template('index.html', error="No valid recommendations found. Try different inputs.")

        recommended_tracks = []
        for track in genre_tracks['tracks']['items']:
            print(f"✅ Processing Track: {track['name']} - {track['artists'][0]['name']}")
            recommended_tracks.append({
                "title": track['name'],
                "artist": ", ".join([a['name'] for a in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "popularity": track['popularity']
            })

        # **3️⃣ Final Check Before Rendering**
        if not recommended_tracks:
            print("⚠️ ERROR: No final recommendations.")
            return render_template('index.html', error="No final recommendations found.")

        print(f"🔹 FINAL RECOMMENDATIONS: {recommended_tracks}")

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")

    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
