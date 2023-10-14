import time
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, redirect, url_for, request,session
from socket import gethostname, gethostbyname
import geocoder
import requests
import spotipy
import logging

TOKEN_INFO = "token_info"


def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for("login", _external=False))

    now = int(time.time())

    is_expired = token_info["expires_at"] - now < 60
    if is_expired:
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info["refresh_token"])

    return token_info


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id="0568384ec4b34425ac205c0149c4e215",
        client_secret="d9c141d58cdc441693eeed4210b48459",
        redirect_uri=url_for("redirect_page", _external=True),
        scope="user-top-read",
    )


def get_location_info():
    try:
        location = geocoder.ip("me")

        if location.ok:
            city = location.city
            state = location.state
            postal_code = location.postal
            return city, state, postal_code
        else:
            return None, None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None


def get_current_weather(location_key=None):
    api_key = "UJWCRUfX4JGRrOOgqzHuwYw4i22KYKYH"
    if location_key is None:
        city, state, postal_code = get_location_info()
        params = {
            "apikey": "UJWCRUfX4JGRrOOgqzHuwYw4i22KYKYH",
            "q": f"{city} {state}",
        }
        response = requests.get(
            "http://dataservice.accuweather.com/locations/v1/cities/search",
            params=params,
        )
        location_key = response.json()[0]["Key"]

    response = requests.get(
        f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={api_key}"
    )
    response_json = response.json()
    weather_text = response_json[0]["WeatherText"]
    temperature_value = round(response_json[0]["Temperature"]["Metric"]["Value"])
    weather_data = {
        "location": city,
        "condition": weather_text,
        "temperature": f"{temperature_value}°C",
    }
    return weather_data


def classify_weather(weather_type):
    weather_type = weather_type.lower()

    sunny_keywords = [
        "sunny",
        "mostly sunny",
        "partly sunny",
        "hazy sunshine",
        "clear",
        "mostly clear",
        "hot",
    ]
    cloudy_keywords = [
        "mostly cloudy",
        "cloudy",
        "dreary (overcast)",
        "fog",
        "hazy moonlight",
        "some clouds",
    ]
    rainy_keywords = ["showers", "rain", "t-storms", "rain and snow"]
    snowy_keywords = [
        "flurries",
        "snow",
        "ice",
        "sleet",
        "freezing rain",
        "mostly cloudy w/ flurries",
        "mostly cloudy w/ snow",
    ]

    if any(keyword in weather_type for keyword in sunny_keywords):
        return "Sunny"
    elif any(keyword in weather_type for keyword in cloudy_keywords):
        return "Cloudy"
    elif any(keyword in weather_type for keyword in rainy_keywords):
        return "Rain"
    elif any(keyword in weather_type for keyword in snowy_keywords):
        return "Snow"
    else:
        return "Unknown"


def get_spotify_instance():
    try:
        token_info = get_token()
    except Exception as e:
        logging.error(f"User not logged in: {str(e)}")
        return None

    access_token = token_info["access_token"]

    return spotipy.Spotify(auth=access_token)


def get_top_tracks(sp, limit=50):
    return sp.current_user_top_tracks(limit=limit, time_range="short_term")


def get_audio_features(sp, track_ids):
    audio_feature_list = [
        (track_id, sp.audio_features(track_id)[0]) for track_id in track_ids
    ]
    return audio_feature_list


def calculate_track_weights(weather_id):
    vw, iw, ew, dw, aw = 0, 0, 0, 0, 0

    if weather_id == "Sunny":
        vw, iw, ew, dw, aw = 1.6, -1.05, 1.7, 1.3, -1.3
    elif weather_id == "Cloudy":
        vw, iw, ew, dw, aw = -1.3, 1.5, -1.6, -1.2, 1.1
    elif weather_id == "Rain":
        vw, iw, ew, dw, aw = -1.5, 1.2, -1.7, -1.3, 1.8
    elif weather_id == "Snow":
        vw, iw, ew, dw, aw = -1.15, 1.5, -1.5, -1.03, 1.2

    return vw, iw, ew, dw, aw


def calculate_sorted_tracks(audio_feature_list, weights):
    sorted_tracks = []
    for track_data in audio_feature_list:
        track_id = track_data[0]
        audio_features = track_data[1]

        valence = audio_features.get("valence", 0.0)
        instrumentalness = audio_features.get("instrumentalness", 0.0)
        energy = audio_features.get("energy", 0.0)
        danceability = audio_features.get("danceability", 0.0)
        acousticness = audio_features.get("acousticness", 0.0)

        weighted_sum = (
            valence * weights[0]
            + instrumentalness * weights[1]
            + energy * weights[2]
            + danceability * weights[3]
            + acousticness * weights[4]
        )

        sorted_tracks.append((track_id, weighted_sum))

    sorted_tracks.sort(key=lambda x: x[1], reverse=True)
    return sorted_tracks


def get_top_five_tracks(sorted_tracks):
    return [x[0] for x in sorted_tracks[:5]]
