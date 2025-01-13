from flask import Flask, request, render_template
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# Spotify API credential
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Set up Spotify client
spotify_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def home():
   
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    
    try:
        # Get user input from the form
        user_genre = request.form.get('genre', 'Pop').strip()
        user_artist = request.form.get('artist', 'Taylor Swift').strip()

        # Search for the artist in Spotify's database
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist named '{user_artist}' found. Please try again!")

        # Extract the artist ID for recommendations
        artist_id = artist_search['artists']['items'][0]['id']

        # Fetch recommendations based on the artist and genre
        recommendations = spotify_client.recommendations(seed_genres=[user_genre.lower()],
                                                         seed_artists=[artist_id],
                                                         limit=10)


        song_recommendations = []
        for track in recommendations['tracks']:
            # Spotify popularity 
            spotify_popularity = track['popularity']

            # Artist match 
            artist_match_score = 100 if any(artist['id'] == artist_id for artist in track['artists']) else 50

            # Genre match 
            genre_match_score = 100 if user_genre.lower() in [g.lower() for g in track['album']['genres']] else 50

            # Adjusted score 
            adjusted_score = (spotify_popularity * 0.5) + (artist_match_score * 0.3) + (genre_match_score * 0.2)

            # Append song details and score
            song_recommendations.append({
                "title": track['name'],
                "artist": ", ".join([artist['name'] for artist in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'],
                "adjusted_score": round(adjusted_score, 2)
            })

        # Sort songs by the score 
        song_recommendations.sort(key=lambda x: x['adjusted_score'], reverse=True)

        return render_template('results.html', recommendations=song_recommendations)

    except Exception as e:
        #  show an error message
        return render_template('index.html', error=f"An error occurred: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
