import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from flask import Flask, request, render_template, jsonify
import os
import random

print("🔍 TEST: Spotify CLIENT_ID =", os.getenv("CLIENT_ID"))
print("🔍 TEST: Spotify CLIENT_SECRET =", os.getenv("CLIENT_SECRET"))

app = Flask(__name__)

# Spotify API Setup
SPOTIFY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"  # Placeholder redirect URI

spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="playlist-modify-public"
))

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
    user_mood = request.form.get('mood', '').strip().lower()
    
    print(f"🔹 Extracted Data - Genre: {user_genre}, Mood: {user_mood}")
    
    if not user_genre or not user_mood:
        print("⚠️ Error: Missing form fields!")
        return render_template('index.html', error="Please fill out all fields.")
    
    try:
        # Step 1: Create a new playlist with a creative name
        creative_name = generate_playlist_name(user_mood)
        user_id = spotify_client.me()['id']
        playlist = spotify_client.user_playlist_create(user=user_id, name=creative_name, public=True, description=f"A playlist for your {user_mood} mood.")
        playlist_id = playlist['id']
        print(f"🎵 Created Playlist: {creative_name} (ID: {playlist_id})")
        
        # Step 2: Search for tracks based on genre and mood
        search_query = f'genre:{user_genre}'
        search_results = spotify_client.search(q=search_query, type='track', limit=20)
        track_uris = [track['uri'] for track in search_results['tracks']['items']]
        
        # Step 3: Add tracks to the created playlist
        if track_uris:
            spotify_client.playlist_add_items(playlist_id, track_uris)
            print(f"✅ Added {len(track_uris)} tracks to the playlist.")
        else:
            print("⚠️ No tracks found for the given genre and mood.")
        
        # Step 4: Fetch playlist details
        playlist_details = spotify_client.playlist(playlist_id)
        playlist_cover = playlist_details['images'][0]['url'] if playlist_details['images'] else "https://via.placeholder.com/500"
        playlist_description = playlist_details.get('description', 'A custom playlist just for you!')
        preview_songs = [track['track']['name'] for track in playlist_details['tracks']['items'][:5]]
        
        # Step 5: Return the playlist preview and link
        playlist_link = playlist['external_urls']['spotify']
        return render_template('results.html', 
                               playlist_name=creative_name, 
                               playlist_link=playlist_link, 
                               playlist_cover=playlist_cover, 
                               playlist_description=playlist_description, 
                               preview_songs=preview_songs, 
                               mood=user_mood)
    
    except spotipy.exceptions.SpotifyException as se:
        print(f"⚠️ Spotify API error: {se}")
        return render_template('index.html', error="Spotify API issue. Please try again later.")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return render_template('index.html', error="An unexpected error occurred. Please try again later.")

def generate_playlist_name(mood, genre, artist):
    """
    Generate a creative playlist name using OpenAI based on mood, genre, and artist.
    """
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    prompt = (f"Create a unique and catchy playlist name based on the following details:
"
              f"Mood: {mood}
"
              f"Genre: {genre}
"
              f"Artist: {artist}
"
              "The name should be creative and fun.")
    
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=20
    )
    
    name = response.choices[0].text.strip()
    return name if name else "Your Custom Playlist")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
