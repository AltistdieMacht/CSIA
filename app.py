import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask, request, render_template, jsonify
import random
import os
print("🔍 TEST: Spotify CLIENT_ID =", os.getenv("CLIENT_ID"))
print("🔍 TEST: Spotify CLIENT_SECRET =", os.getenv("CLIENT_SECRET"))

app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Flask App is Running on Render!"

# Spotify API Setup
SPOTIFY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")

spotify_client = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
    )
)

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
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
        print("⚠️ Error: Missing form fields!")
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 1️⃣ Suche nach Artist-ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        print(f"🔹 Spotify Artist Search Result: {artist_search}")

        if not artist_search['artists']['items']:
            print(f"⚠️ Error: No artist found for '{user_artist}'")
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']

        # 2️⃣ Ähnliche Künstler finden
        related_artists = spotify_client.artist_related_artists(artist_id)
        if not related_artists['artists']:
            print("⚠️ Error: No related artists found!")
            return render_template('index.html', error="No related artists found.")

        similar_artists = [artist['id'] for artist in related_artists['artists'][:5]]

        # 3️⃣ Top-Tracks der ähnlichen Künstler holen
        recommended_tracks = []
        for artist in similar_artists:
            top_tracks = spotify_client.artist_top_tracks(artist)
            if not top_tracks['tracks']:
                print(f"⚠️ Warning: No tracks found for artist {artist}")
                continue

            for track in top_tracks['tracks'][:2]:  # Maximal 2 Songs pro Künstler
                recommended_tracks.append({
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "link": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None
                })

        print(f"🔹 Recommended Tracks: {recommended_tracks}")

        # Falls keine Songs gefunden wurden
        if not recommended_tracks:
            print("⚠️ Error: No recommendations found!")
            return render_template('index.html', error="No recommendations found. Try different inputs.")

        # Songs zufällig sortieren
        import random
        random.shuffle(recommended_tracks)

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(debug=True)
