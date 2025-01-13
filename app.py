from flask import Flask, request, render_template
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials

# Flask app setup
app = Flask(__name__)

# Spotify API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Ensure credentials are set
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise EnvironmentError("Spotify API credentials are not set in environment variables.")

# Spotify client setup
spotify_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def home():
    """
    Render the homepage with a form for user input.
    """
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Handle song recommendation requests based on user input.
    """
    try:
        # Get user input
        user_genre = request.form.get('genre', '').strip()
        user_artist = request.form.get('artist', '').strip()

        # Validate user input
        if not user_genre or not user_artist:
            return render_template('index.html', error="Please provide both a genre and an artist.")

        # Search for the artist
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist named '{user_artist}' found. Please try again.")

        # Get artist ID
        artist_id = artist_search['artists']['items'][0]['id']

        # Fetch song recommendations
        recommendations = spotify_client.recommendations(seed_genres=[user_genre.lower()],
                                                         seed_artists=[artist_id],
                                                         limit=10)

        # Process recommendations
        song_recommendations = []
        for track in recommendations['tracks']:
            # Calculate adjusted score
            spotify_popularity = track['popularity']
            artist_match_score = 100 if any(artist['id'] == artist_id for artist in track['artists']) else 50
            genre_match_score = 100 if user_genre.lower() in [g.lower() for g in track.get('album', {}).get('genres', [])] else 50
            adjusted_score = (spotify_popularity * 0.5) + (artist_match_score * 0.3) + (genre_match_score * 0.2)

            # Append track details
            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "adjusted_score": round(adjusted_score, 2)
            })

        # Sort by adjusted score
        song_recommendations.sort(key=lambda x: x['adjusted_score'], reverse=True)

        return render_template('results.html', recommendations=song_recommendations)

    except Exception as e:
        # Log the error and show a user-friendly message
        print(f"Error occurred: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(debug=True)
