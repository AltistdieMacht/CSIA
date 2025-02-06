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
def recommend_taste_based():
    print(f"🔹 Incoming request: {request.method}")

    if request.method == 'GET':
        return render_template('index.html')

    print(f"🔹 Form Data Received: {request.form}")

    user_genre = request.form.get('genre', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()
    user_mood = request.form.get('mood', '').strip()

    if not user_genre or not user_artist or not user_mood:
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 1️⃣ Identify User Preferences - Get the artist ID and associated genres
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']
        artist_genres = artist_search['artists']['items'][0].get('genres', [])

        # 2️⃣ Build a Taste Profile - Use artist genres or fallback to user input genre
        genre_query = ' '.join([f'genre:{g}' for g in artist_genres]) if artist_genres else f'genre:{user_genre}'
        similar_tracks = spotify_client.search(q=genre_query, type='track', limit=20)
        
        recommended_tracks = []
        for track in similar_tracks['tracks']['items']:
            track_genres = get_artist_genres(track['artists'][0]['id'])
            track_features = spotify_client.audio_features(track['id'])[0]  # Get detailed song features

            if any(genre in track_genres for genre in artist_genres):
                popularity_score = calculate_custom_popularity(track['popularity'])
                recommendation_score = calculate_recommendation_score(popularity_score, user_mood, track_features)
                recommended_tracks.append({
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "link": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                    "popularity": popularity_score,
                    "recommendation_score": recommendation_score
                })

        # 3️⃣ Rank by Taste Matching
        recommended_tracks = sorted(recommended_tracks, key=lambda x: x['recommendation_score'], reverse=True)

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

def calculate_custom_popularity(spotify_popularity):
    """
    Custom Popularity Score: Adjusts Spotify's 0-100 scale for better ranking.
    """
    return round((spotify_popularity / 100) * 10, 2)

def calculate_recommendation_score(popularity, mood, track_features):
    """
    Calculates a final recommendation score based on:
    - Popularity (how well-known the track is)
    - Energy, Valence (happiness), and Danceability (Spotify audio features)
    - Mood weighting (adjusts relevance based on user-selected mood)
    """
    mood_weights = {
        "happy": track_features.get("valence", 0.5) * 1.5 + track_features.get("danceability", 0.5) * 1.1,
        "energetic": track_features.get("energy", 0.5) * 1.5 + track_features.get("danceability", 0.5) * 1.3,
        "calm": track_features.get("valence", 0.5) * 0.8 + track_features.get("energy", 0.5) * 0.7,
        "sad": track_features.get("valence", 0.5) * 0.6 + track_features.get("energy", 0.5) * 0.8,
    }
    mood_score = mood_weights.get(mood.lower(), 1)
    return round(popularity * mood_score, 2)

def get_artist_genres(artist_id):
    artist = spotify_client.artist(artist_id)
    return artist.get('genres', [])
def get_audio_features(track_id):
    """Fetch audio features for a given track ID with error handling."""
    try:
        features = spotify_client.audio_features(track_id)
        if not features or features[0] is None:
            print(f"⚠️ ERROR: No audio features found for track {track_id}")
            return {}
        return features[0]
    except spotipy.exceptions.SpotifyException as e:
        print(f"⚠️ Spotify API error on audio-features: {e}")
        return {}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
