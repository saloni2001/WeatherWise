from functions import *


app = Flask(__name__)
app.config["SESSION_COOKIE_NAME"] = "Spotify Cookie"
app.secret_key = "d9c141d58cdc441693eeed4210b48459"


@app.route("/")
def login():
    auth_url = create_spotify_oauth().get_authorize_url()

    return redirect(auth_url)


@app.route("/redirect")
def redirect_page():
    session.clear()

    code = request.args.get("code")

    token_info = create_spotify_oauth().get_access_token(code)

    session[TOKEN_INFO] = token_info

    return redirect(url_for("recommendation", _external=True))


@app.route("/getRecommendation")
def recommendation():
    sp = get_spotify_instance()
    if sp is None:
        return redirect("/")
    top_track_items = get_top_tracks(sp)
    top_track_ids = [track["id"] for track in top_track_items["items"]]
    audio_feature_list = get_audio_features(sp, top_track_ids)
    weather_data = get_current_weather()
    weather_id = classify_weather(weather_data.get("condition"))
    vw, iw, ew, dw, aw = calculate_track_weights(weather_id)
    sorted_tracks = calculate_sorted_tracks(audio_feature_list, (vw, iw, ew, dw, aw))
    top_five_track_ids = get_top_five_tracks(sorted_tracks)
    top_tracks = [
        {
            "song": track["name"],
            "artist": ", ".join([artist["name"] for artist in track["artists"]]),
        }
        for track in top_track_items["items"]
    ]
    recommended_track_items = sp.recommendations(
        seed_tracks=top_five_track_ids, limit=20
    )
    recommended_tracks = [
        {
            "song": track["name"],
            "artist": ", ".join([artist["name"] for artist in track["artists"]]),
            "link": track["external_urls"]["spotify"],
        }
        for track in recommended_track_items["tracks"]
    ]
    return render_template(
        "recommendation.html",
        weather=weather_data,
        top_tracks=top_tracks,
        recommended_tracks=recommended_tracks,
    )


app.run(debug=True)
