
import os
import joblib
import requests

from functools import lru_cache
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# TMDB API configuration
TMDB_TOKEN = os.getenv("TMDB_READ_ACCESS_TOKEN")
TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

# Configure TMDB request session
session = requests.Session()

if TMDB_TOKEN:
    session.headers.update({
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    })

# Load trained ML model
model = joblib.load("model/recommender.joblib")

movies = model["movies"]
matrix = model["matrix"]


# Fetch movie poster from TMDB
@lru_cache(maxsize=500)
def get_movie_poster(movie_title):

    if not TMDB_TOKEN:
        print("TMDB token not found in .env")
        return None

    try:
        response = session.get(
            f"{TMDB_API_URL}/search/movie",
            params={
                "query": movie_title,
                "language": "en-US",
                "include_adult": "false"
            },
            timeout=10
        )

        response.raise_for_status()

        results = response.json().get("results", [])

        # Prefer an exact title match with a poster
        selected = next(
            (
                item for item in results
                if item.get("title", "").casefold()
                == movie_title.casefold()
                and item.get("poster_path")
            ),
            None
        )

        # Otherwise use the first result that has a poster
        if selected is None:
            selected = next(
                (item for item in results if item.get("poster_path")),
                None
            )

        if selected:
            return TMDB_IMAGE_URL + selected["poster_path"]

        return None

    except requests.RequestException as error:
        print(f"TMDB API error for {movie_title}: {error}")
        return None


# Home page
@app.route("/")
def home():

    movie_titles = movies["title"].tolist()

    return render_template(
        "index.html",
        movies=movie_titles
    )


# Movie recommendation API
@app.route("/recommend", methods=["POST"])
def recommend():

    body = request.get_json(silent=True) or {}
    selected_movie = body.get("movie", "")

    if not isinstance(selected_movie, str) or not selected_movie.strip():
        return jsonify({"error": "Please enter a movie name"}), 400

    selected_movie = selected_movie.strip()

    matches = movies[
        movies["title"].str.casefold() == selected_movie.casefold()
    ]

    if matches.empty:
        return jsonify({"error": "Movie not found in dataset"}), 404

    movie_index = matches.index[0]

    scores = cosine_similarity(
        matrix[movie_index],
        matrix
    ).flatten()

    similar_movies = scores.argsort()[::-1]

    recommendations = []

    for index in similar_movies:

        if index == movie_index:
            continue

        movie = movies.iloc[index]
        title = movie["title"]

        # Get poster from TMDB
        poster = get_movie_poster(title)

        recommendations.append({
            "title": title,
            "overview": movie["overview"],
            "similarity": round(float(scores[index]), 3),
            "poster": poster
        })

        if len(recommendations) == 10:
            break

    return jsonify(recommendations)


if __name__ == "__main__":
    app.run(debug=True)
