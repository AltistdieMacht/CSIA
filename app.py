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
        # Form-Daten abrufen
        user_genre = request.form.get('genre', 'Pop').strip().lower()
        user_artist = request.form.get('artist', 'Taylor Swift').strip()

        # Artist-ID abrufen
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'. Try again!")

        artist_id = artist_search['artists']['items'][0]['id']

        # Unterstützte Genres prüfen
        supported_genres = spotify_client.recommendation_genre_seeds()['genres']
        if user_genre not in supported_genres:
            return render_template('index.html', error=f"Genre '{user_genre}' not supported. Try one of: {', '.join(supported_genres)}")

        # Empfehlungen abrufen
        recommendations = spotify_client.recommendations(seed_genres=[user_genre],
                                                         seed_artists=[artist_id],
                                                         limit=10)

        if not recommendations['tracks']:
            return render_template('index.html', error="No recommendations found. Try different inputs!")

        # Ergebnisse formatieren
        song_recommendations = []
        for track in recommendations['tracks']:
            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url']
            })

        # Ergebnisse anzeigen
        return render_template('results.html', recommendations=song_recommendations)

    except Exception as e:
        print(f"Error occurred: {e}")
        return render_template('index.html', error="An error occurred. Please try again later.")


if __name__ == '__main__':
    app.run(debug=True)
