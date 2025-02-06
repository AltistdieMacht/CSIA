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

@app.route('/home')
def home():
    return "✅ Flask App is Running!"

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
        # Search for artist ID
        artist_search = spotify_client.search(q=f"artist:{user_artist}", type='artist', limit=1)
        print(f"🔹 Spotify Artist Search Result: {artist_search}")
        
        if not artist_search['artists']['items']:
            print(f"⚠️ Error: No artist found for '{user_artist}'")
            return render_template('index.html', error=f"No artist found for '{user_artist}'.")
        
        artist_id = artist_search['artists']['items'][0]['id']
        
        # Get related artists
        related_artists = spotify_client.artist_related_artists(artist_id)
        similar_artist_ids = [artist['id'] for artist in related_artists['artists'][:5]]
        
        # Get tracks from related artists and genre
        recommended_tracks = []
        for artist_id in similar_artist_ids:
            artist_top_tracks = spotify_client.artist_top_tracks(artist_id)
            recommended_tracks.extend(artist_top_tracks['tracks'])
        
        if not recommended_tracks:
            print("⚠️ No matching songs found! Fetching genre-based tracks as fallback.")
            genre_tracks = spotify_client.search(q=f'genre:{user_genre}', type='track', limit=10)
            recommended_tracks = genre_tracks['tracks']['items']
        
        processed_tracks = []
        for track in recommended_tracks:
            print(f"✔️ Processing Track: {track['name']} - {track['artists'][0]['name']}")
            
            track_features = get_audio_features(track['id'])
            if not track_features:
                print(f"⚠️ Track '{track['name']}' skipped – no audio features available.")
                continue
            
            # Calculate mood matching score
            mood_score = calculate_mood_match(track_features, user_mood)
            
            # Calculate final recommendation score
            recommendation_score = (calculate_custom_popularity(track['popularity']) + mood_score) / 2
            
            processed_tracks.append({
                "title": track['name'],
                "artist": ", ".join([a['name'] for a in track['artists']]),
                "link": track['external_urls']['spotify'],
                "image": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "popularity": recommendation_score
            })
        
        # Sort by combined popularity and mood match score
        processed_tracks = sorted(processed_tracks, key=lambda x: x['popularity'], reverse=True)
        print(f"🔹 Final Sorted Tracks: {processed_tracks}")
        
        return render_template('results.html', recommendations=processed_tracks, mood=user_mood)
    
    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

def calculate_custom_popularity(spotify_popularity):
    """
    Custom Popularity Score: Converts Spotify's popularity (0-100) to a 1-10 scale.
    """
    return round((spotify_popularity / 100) * 10, 2)

def get_audio_features(track_id):
    """
    Fetch audio features for a given track and handle errors.
    """
    try:
        features = spotify_client.audio_features(track_id)
        if not features or features[0] is None:
            print(f"⚠️ No audio features found for track ID: {track_id}")
            return {}
        return features[0]
    except spotipy.exceptions.SpotifyException as e:
        print(f"⚠️ Spotify API error for audio features (403 or Rate Limit?): {e}")
        return {}

def calculate_mood_match(track_features, user_mood):
    """
    Assigns a mood score based on Spotify's valence and energy values.
    """
    mood_weights = {
        "happy": track_features.get("valence", 0.5) * 1.5 + track_features.get("danceability", 0.5) * 1.2,
        "energetic": track_features.get("energy", 0.5) * 1.5 + track_features.get("danceability", 0.5) * 1.3,
        "calm": track_features.get("valence", 0.5) * 0.8 + track_features.get("energy", 0.5) * 0.7,
        "sad": track_features.get("valence", 0.5) * 0.6 + track_features.get("energy", 0.5) * 0.8,
    }
    return mood_weights.get(user_mood.lower(), 1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)