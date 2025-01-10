from flask import Flask, request, render_template
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# Spotify API credentials
SPOTIFY_CLIENT_ID = "your_client_id"
SPOTIFY_CLIENT_SECRET = "your_client_secret"

# Set up Spotify client
spotify_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def home():
    # Display the homepage with the form
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        # Get user input
        user_genre = request.form.get('genre', 'Pop')
        user_artist = request.form.get('artist', 'Taylor Swift')
        user_mood = request.form.get('mood', 'Happy')

        # Search for the artist
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist named '{user_artist}' found. Try again!")

        # Get artist ID
        artist_id = artist_search['artists']['items'][0]['id']

        # Fetch recommendations
        recommendations = spotify_client.recommendations(seed_genres=[user_genre.lower()],
                                                         seed_artists=[artist_id],
                                                         limit=5)

        # Process recommendations
        song_recommendations = []
        for track in recommendations['tracks']:
            spotify_popularity = track['popularity']
            mood_match_score = 100 if user_mood.lower() in track['name'].lower() else 50
            genre_match_score = 100 if user_genre.lower() in [g.lower() for g in track['album']['genres']] else 50

            # Custom popularity calculation
            custom_popularity = (spotify_popularity * 0.6) + (mood_match_score * 0.3) + (genre_match_score * 0.1)

            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'],
                "custom_popularity": round(custom_popularity, 2)
            })

        # Sort songs by custom popularity
        song_recommendations.sort(key=lambda x: x['custom_popularity'], reverse=True)

        # Render the results page
        return render_template('results.html', recommendations=song_recommendations)

    except Exception as e:
        # Handle errors
        return render_template('index.html', error=f"An error occurred: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
