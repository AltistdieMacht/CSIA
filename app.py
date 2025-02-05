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
    print(f"🔹 Incoming request: {request.method}")

    if request.method == 'GET':
        print("✅ GET request received. Returning index.html")
        return render_template('index.html')

    print(f"🔹 Form Data: {request.form}")

    user_genre = request.form.get('genre', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()
    user_mood = request.form.get('mood', '').strip()

    print(f"🔹 Extracted Data - Genre: {user_genre}, Artist: {user_artist}, Mood: {user_mood}")

    if not user_genre or not user_artist or not user_mood:
        print("⚠️ Error: Missing form fields!")
        return render_template('index.html', error="Please fill out all fields: Genre, Artist, and Mood.")

    try:
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        print(f"🔹 Spotify Artist Search Result: {artist_search}")

        if not artist_search['artists']['items']:
            print(f"⚠️ Error: No artist found for {user_artist}")
            return render_template('index.html', error=f"No artist found for '{user_artist}'. Please try again.")

        artist_id = artist_search['artists']['items'][0]['id']

        recommendations = spotify_client.recommendations(
            seed_genres=[user_genre],
            seed_artists=[artist_id],
            limit=10
        )

        print(f"🔹 Spotify Recommendations Result: {recommendations}")

        if not recommendations['tracks']:
            print("⚠️ Error: No recommendations found!")
            return render_template('index.html', error="No recommendations found. Try different inputs.")

        # Format results
        song_recommendations = []
        for track in recommendations['tracks']:
            spotify_popularity = track['popularity']
            mood_match_score = 100 if user_mood.lower() in track['name'].lower() else 50

            popularity = (spotify_popularity * 0.7) + (mood_match_score * 0.3)

            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "popularity": round(popularity, 2)
            })

        song_recommendations.sort(key=lambda x: x['popularity'], reverse=True)

        return render_template('results.html', recommendations=song_recommendations, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")


if __name__ == '__main__':
    app.run(debug=True)