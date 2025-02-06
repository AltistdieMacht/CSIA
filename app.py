import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask, request, render_template, jsonify
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
        print("⚠️ Error: Missing form fields!")
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 1️⃣ Get Artist ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']
        artist_genres = artist_search['artists']['items'][0].get('genres', [])
        print(f"🔹 Artist Genres: {artist_genres}")

        # 2️⃣ Use a broader track search instead of just top tracks
        track_query = f"genre:{user_genre} mood:{user_mood}" if user_genre else f"mood:{user_mood}"
        print(f"🔹 Searching for tracks with query: {track_query}")

        genre_tracks = spotify_client.search(q=track_query, type='track', limit=20)
        if 'tracks' in genre_tracks and 'items' in genre_tracks['tracks']:
            recommended_tracks = [
                {
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "link": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                    "popularity": calculate_custom_popularity(track['popularity'])
                }
                for track in genre_tracks['tracks']['items']
            ]
        else:
            print("⚠️ No songs found for the given genre and mood!")
            return render_template('index.html', error="No valid recommendations found. Try different inputs.")

        # 3️⃣ Sort by Popularity Score
        recommended_tracks = sorted(recommended_tracks, key=lambda x: x['popularity'], reverse=True)
        print(f"🔹 Final Sorted Tracks: {recommended_tracks}")

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

def calculate_custom_popularity(spotify_popularity):
    """ Adjusts Spotify's 0-100 popularity score to a custom scale. """
    return round((spotify_popularity / 100) * 10, 2)  # Scale to 1-10

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
