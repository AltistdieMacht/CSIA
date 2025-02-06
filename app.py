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
        # 1️⃣ Search for Artist ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        print(f"🔹 Spotify Artist Search Result: {artist_search}")

        if not artist_search['artists']['items']:
            print(f"⚠️ Error: No artist found for '{user_artist}'")
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']
        artist_genres = artist_search['artists']['items'][0]['genres']
        print(f"🔹 Artist Genres: {artist_genres}")

        # 2️⃣ Find Top Artists in the Same Genre
        genre_query = ' '.join([f'genre:{g}' for g in artist_genres]) if artist_genres else f'genre:{user_genre}'
        genre_artists = spotify_client.search(q=genre_query, type='artist', limit=5)
        
        if 'artists' in genre_artists and 'items' in genre_artists['artists']:
            similar_artists = [artist['id'] for artist in genre_artists['artists']['items']]
            print(f"🔹 Found alternative artists: {similar_artists}")
        else:
            print("⚠️ No alternative artists found via search!")
            return render_template('index.html', error="Could not find similar artists.")

        # 3️⃣ Get Top Tracks from Similar Artists, Ensuring Genre Match
        recommended_tracks = []
        for artist in similar_artists:
            top_tracks = spotify_client.artist_top_tracks(artist)
            
            for track in top_tracks['tracks'][:2]:  # Max 2 songs per artist
                track_genres = get_artist_genres(track['artists'][0]['id'])
                
                if any(genre in track_genres for genre in artist_genres):  # Ensure genre match
                    popularity_score = calculate_custom_popularity(track['popularity'])
                    recommended_tracks.append({
                        "title": track['name'],
                        "artist": ", ".join([a['name'] for a in track['artists']]),
                        "link": track['external_urls']['spotify'],
                        "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                        "popularity": popularity_score  # Custom Popularity Score
                    })

        # 4️⃣ Sort by Popularity
        recommended_tracks = sorted(recommended_tracks, key=lambda x: x['popularity'], reverse=True)
        print(f"🔹 Final Sorted Tracks: {recommended_tracks}")

        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

def calculate_custom_popularity(spotify_popularity):
    """
    Custom Popularity Score: Adjusts Spotify's 0-100 scale for better ranking.
    """
    return round((spotify_popularity / 100) * 10, 2)  # Scale to 1-10


def get_artist_genres(artist_id):
    """ Fetch the genres for a given artist ID """
    artist = spotify_client.artist(artist_id)
    return artist.get('genres', [])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)