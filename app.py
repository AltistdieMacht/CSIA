import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from flask import Flask, request, render_template, jsonify
import os
import random
import openai

print("🔍 TEST: Spotify CLIENT_ID =", os.getenv("CLIENT_ID"))
print("🔍 TEST: Spotify CLIENT_SECRET =", os.getenv("CLIENT_SECRET"))

app = Flask(__name__)

# Spotify API Setup
SPOTIFY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"  # Placeholder redirect URI
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    user_artist = request.form.get('artist', '').strip()
    
    print(f"🔹 Extracted Data - Genre: {user_genre}, Mood: {user_mood}, Artist: {user_artist}")
    
    if not user_genre or not user_mood or not user_artist:
        print("⚠️ Error: Missing form fields!")
        return render_template('index.html', error="Please fill out all fields.")
    
    try:
        # Step 1: Generate a creative playlist name using OpenAI
        creative_name = generate_playlist_name(user_mood, user_genre, user_artist)
        user_id = spotify_client.me()['id']
        playlist = spotify_client.user_playlist_create(user=user_id, name=creative_name, public=True, description=f"A playlist for your {user_mood} mood.")
        playlist_id = playlist['id']
        print(f"🎵 Created Playlist: {creative_name} (ID: {playlist_id})")
        
        # Step 2: Search for tracks based on genre and mood
        search_query = f'genre:{user_genre} artist:{user_artist}'
        search_results = spotify_client.search(q=search_query, type='track', limit=20)
        track_uris = [track['uri'] for track in search_results['tracks']['items']]
        
        # Step 3: OpenAI Backup if no tracks found
        if not track_uris:
            print("⚠️ No tracks found in Spotify. Using OpenAI for backup suggestions.")
            suggested_tracks = get_suggested_tracks(user_mood, user_genre, user_artist)
            for suggested_track in suggested_tracks:
                track_search = spotify_client.search(q=suggested_track, type='track', limit=1)
                if track_search['tracks']['items']:
                    track_uris.append(track_search['tracks']['items'][0]['uri'])
            print(f"✅ Added {len(track_uris)} tracks from OpenAI suggestions.")
        
        # Step 4: Add tracks to the created playlist
        if track_uris:
            spotify_client.playlist_add_items(playlist_id, track_uris)
            print(f"✅ Added {len(track_uris)} tracks to the playlist.")
        else:
            print("⚠️ No tracks found or suggested.")
        
        # Step 5: Fetch playlist details
        playlist_details = spotify_client.playlist(playlist_id)
        playlist_cover = playlist_details['images'][0]['url'] if playlist_details['images'] else "https://via.placeholder.com/500"
        playlist_description = playlist_details.get('description', 'A custom playlist just for you!')
        preview_songs = [track['track']['name'] for track in playlist_details['tracks']['items'][:5]]
        
        # Step 6: Return the playlist preview and link
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
    prompt = (f"Create a unique and catchy playlist name based on the following details:\n"
              f"Mood: {mood}\n"
              f"Genre: {genre}\n"
              f"Artist: {artist}\n"
              "The name should be creative and fun.")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a playlist name generator."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=20
    )
    
    name = response.choices[0].message['content'].strip()
    return name if name else "Your Custom Playlist"

def get_suggested_tracks(mood, genre, artist):
    """
    Use OpenAI to suggest tracks based on mood, genre, and artist.
    """
    prompt = (f"Suggest 5 song titles that match the following criteria:\n"
              f"Mood: {mood}\n"
              f"Genre: {genre}\n"
              f"Similar to: {artist}\n"
              "Provide only the song titles in a comma-separated format.")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a music recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=50
    )
    suggestions = response.choices[0].message['content'].strip()
    return [song.strip() for song in suggestions.split(',')] if suggestions else []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
