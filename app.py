import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask, request, render_template, jsonify
import random

app = Flask(__name__)

# Spotify API Setup
SPOTIFY_CLIENT_ID = "YOUR_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_CLIENT_SECRET"

spotify_client = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
    )
)

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'GET':
        return render_template('index.html')

    user_genre = request.form.get('genre', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()
    user_mood = request.form.get('mood', '').strip()

    if not user_genre or not user_artist or not user_mood:
        return render_template('index.html', error="Please fill out all fields.")

    try:
        # 1️⃣ Fetch artist ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        if not artist_search['artists']['items']:
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")

        artist_id = artist_search['artists']['items'][0]['id']

        # 2️⃣ Find similar artists
        related_artists = spotify_client.artist_related_artists(artist_id)
        similar_artists = [artist['id'] for artist in related_artists['artists'][:5]]

        # 3️⃣ Get top tracks from similar artists
        recommended_tracks = []
        for artist in similar_artists:
            top_tracks = spotify_client.artist_top_tracks(artist)
            for track in top_tracks['tracks'][:2]:  # Take the top 2 songs per artist
                recommended_tracks.append({
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "link": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None
                })

        # 4️⃣ Shuffle and return the recommendations
        random.shuffle(recommended_tracks)
        return render_template('results.html', recommendations=recommended_tracks, mood=user_mood)

    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    app.run(debug=True)
