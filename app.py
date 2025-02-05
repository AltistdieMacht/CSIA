from flask import Flask, request, render_template
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

@app.route('/')
def home():
    """Render the homepage."""
    return render_template('index.html')

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    """Handle recommendation requests."""
    try:
        if request.method == 'GET':
            return render_template('index.html')  # Zeigt einfach das Formular an

        # Ab hier läuft nur der POST-Teil
        user_genre = request.form.get('genre', '').strip().lower()
        user_artist = request.form.get('artist', '').strip()
        user_mood = request.form.get('mood', '').strip()

        # Validate inputs
        if not user_genre or not user_artist or not user_mood:
            return render_template('index.html', error="Please fill out all fields: Genre, Artist, and Mood.")

        # Search for artist
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'. Please try again.")

        artist_id = artist_search['artists']['items'][0]['id']

        # Fetch recommendations
        recommendations = spotify_client.recommendations(
            seed_genres=[user_genre],
            seed_artists=[artist_id],
            limit=10
        )

        if not recommendations['tracks']:
            return render_template('index.html', error="No recommendations found. Try different inputs.")

        # Format results with custom score
        song_recommendations = []
        for track in recommendations['tracks']:
            spotify_popularity = track['popularity']
            mood_match_score = 100 if user_mood.lower() in track['name'].lower() else 50

            # Calculate custom score
            popularity = (spotify_popularity * 0.7) + (mood_match_score * 0.3)

            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "popularity": round(popularity, 2)
            })

        # Sort recommendations by custom score
        song_recommendations.sort(key=lambda x: x['popularity'], reverse=True)

        return render_template('results.html', recommendations=song_recommendations, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"Spotify API error: {se}")
        return render_template('index.html', error="There was an issue with the Spotify API. Please try again later.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")


if __name__ == '__main__':
    app.run(debug=True)