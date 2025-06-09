import os
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# Load API Keys from Environment Variables
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5000/callback")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Spotify Auth Setup
sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="playlist-modify-public")

openai.api_key = OPENAI_API_KEY


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    """ Redirect user to Spotify login """
    return redirect(sp_oauth.get_authorize_url())


@app.route('/callback')
def callback():
    """ Handle Spotify OAuth callback """
    session.clear()
    token_info = sp_oauth.get_access_token(request.args.get('code'))
    session["token_info"] = token_info
    return redirect(url_for("index"))


def get_spotify_client():
    """ Return an authenticated Spotify client or None """
    token_info = session.get("token_info")
    return spotipy.Spotify(auth=token_info["access_token"]) if token_info else None


@app.route('/recommend', methods=['POST'])
def recommend():
    user_genre = request.form.get('genre', '').strip().lower()
    user_mood = request.form.get('mood', '').strip().lower()
    user_artist = request.form.get('artist', '').strip()

    if not user_genre or not user_mood or not user_artist:
        return render_template('index.html', error="All fields are required!")

    spotify_client = get_spotify_client()
    if not spotify_client:
        return redirect(url_for('login'))

    # Generate Playlist Name
    playlist_name = generate_playlist_name(user_mood, user_genre, user_artist)

    # Get track URIs
    track_uris = get_songs(spotify_client, user_genre, user_artist, user_mood)

    if not track_uris:
        return render_template('index.html', error="No songs found. Try again!")

    # Create Playlist & Add Songs
    user_id = spotify_client.me()["id"]
    playlist = spotify_client.user_playlist_create(user_id, playlist_name, public=True)
    spotify_client.playlist_add_items(playlist["id"], track_uris)

    # Get Playlist Cover
    playlist_cover = get_playlist_cover(spotify_client, playlist["id"])

    return render_template('results.html',
                           playlist_name=playlist_name,
                           playlist_link=playlist["external_urls"]["spotify"],
                           playlist_cover=playlist_cover,
                           preview_songs=get_track_names(spotify_client, track_uris),
                           mood=user_mood)


def generate_playlist_name(mood, genre, artist):
    """ Generate a creative playlist name using OpenAI """
    prompt = f"Create a fun playlist name for mood: {mood}, genre: {genre}, artist: {artist}."

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a creative music assistant."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=20
    )
    return response["choices"][0]["message"]["content"].strip()


def get_songs(spotify_client, genre, artist, mood):
    """ Get song URIs either from Spotify search or OpenAI suggestions """
    search_query = f'genre:{genre} artist:{artist}'
    search_results = spotify_client.search(q=search_query, type='track', limit=10)
    track_uris = [track['uri'] for track in search_results['tracks']['items']]

    if not track_uris:
        suggested_tracks = get_suggested_tracks(mood, genre, artist)
        for track in suggested_tracks:
            search_res = spotify_client.search(q=track, type='track', limit=1)
            if search_res['tracks']['items']:
                track_uris.append(search_res['tracks']['items'][0]['uri'])

    return track_uris[:10]  # Max 10 tracks per playlist


def get_suggested_tracks(mood, genre, artist):
    """ Use OpenAI to suggest song titles if none are found """
    prompt = f"Suggest 5 songs for mood: {mood}, genre: {genre}, similar to artist: {artist}."

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a music expert."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=50
    )

    return [song.strip() for song in response["choices"][0]["message"]["content"].split(',')]


def get_playlist_cover(spotify_client, playlist_id):
    """ Retrieve playlist cover URL """
    covers = spotify_client.playlist_cover_image(playlist_id)
    return covers[0]["url"] if covers else None


def get_track_names(spotify_client, track_uris):
    """ Get track names for preview display """
    tracks = spotify_client.tracks(track_uris)["tracks"]
    return [track["name"] for track in tracks]


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
