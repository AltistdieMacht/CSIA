from flask import Flask, request, render_template, jsonify
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Ensure Spotify credentials are set
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise EnvironmentError("Spotify API credentials are not set.")

# Spotify client setup
spotify_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# Valid Spotify genres
valid_genres = ["pop", "rock", "hip-hop", "classical", "jazz", "blues", "edm", "country"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        # Get user input
        user_genre = request.form.get('genre', '').strip().lower()
        user_artist = request.form.get('artist', '').strip()

        # Validate inputs
        if not user_genre or user_genre not in valid_genres:
            user_genre = "pop"  # Default to 'pop' if invalid
        if not user_artist:
            return jsonify({"error": "Please provide a valid artist."})

        # Search for the artist
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return jsonify({"error": f"No artist named '{user_artist}' found. Please try again."})

        # Get artist ID
        artist_id = artist_search['artists']['items'][0]['id']

        # Fetch recommendations
        recommendations = spotify_client.recommendations(seed_genres=[user_genre],
                                                         seed_artists=[artist_id],
                                                         limit=10)

        # Process recommendations
        song_recommendations = []
        for track in recommendations['tracks']:
            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None
            })

        return jsonify({"recommendations": song_recommendations})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."})

if __name__ == '__main__':
    app.run(debug=True)
