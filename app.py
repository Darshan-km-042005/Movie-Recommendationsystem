import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import joblib
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import requests
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
MODEL_PATH = BASE_DIR / "model" / "recommender.joblib"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Recommendation model not found at {MODEL_PATH}. "
        "Run `python train_model.py` to create it."
    )

model = joblib.load(MODEL_PATH)
movies = model["movies"]
matrix = model["matrix"]
TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w342"
logger = logging.getLogger(__name__)

if not {"id", "title", "overview"}.issubset(movies.columns):
    raise ValueError("The recommendation model is missing required movie data.")
if matrix.shape[0] != len(movies):
    raise ValueError("The recommendation model and movie data have different sizes.")
movie_ids = {int(movie_id) for movie_id in movies["id"]}

app = Flask(__name__)


@app.get("/")
def home():
    movie_titles = movies["title"].tolist()
    return render_template(
        "index.html",
        movies=movie_titles,
        movie_count=len(movie_titles),
    )


@app.post("/recommend")
def recommend():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("movie"), str):
        return jsonify({"error": "Please provide a movie title."}), 400

    selected_movie = payload["movie"].strip()
    if not selected_movie:
        return jsonify({"error": "Please enter a movie title."}), 400

    matches = movies[movies["title"].str.casefold() == selected_movie.casefold()]
    if matches.empty:
        return jsonify({"error": "We couldn't find that movie. Choose a title from the suggestions."}), 404

    movie_index = int(matches.index[0])
    scores = cosine_similarity(matrix[movie_index], matrix).ravel()
    ranked_indices = scores.argsort()[::-1]

    recommendations = []
    for index in ranked_indices:
        if index == movie_index:
            continue

        movie = movies.iloc[index]
        recommendations.append(
            {
                "title": movie["title"],
                "overview": movie["overview"],
                "similarity": round(float(scores[index]), 3),
                "id": int(movie["id"]),
            }
        )
        if len(recommendations) == 10:
            break

    return jsonify(recommendations)


@lru_cache(maxsize=4096)
def get_movie_poster(movie_id, token):
    try:
        response = requests.get(
            f"{TMDB_API_URL}/movie/{movie_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        response.raise_for_status()
        movie_data = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("TMDb poster lookup failed for movie ID %s: %s", movie_id, error)
        status_code = (
            error.response.status_code
            if isinstance(error, requests.HTTPError) and error.response is not None
            else None
        )
        if status_code in (401, 403):
            return None, "auth"
        if status_code == 404:
            return None, "not_found"
        if isinstance(error, (requests.Timeout, requests.ConnectionError)):
            return None, "network"
        return None, "service"

    poster_path = movie_data.get("poster_path") if isinstance(movie_data, dict) else None
    if (
        not isinstance(poster_path, str)
        or not poster_path.startswith("/")
        or poster_path.startswith("//")
    ):
        return None, None
    return f"{TMDB_IMAGE_URL}{poster_path}", None


@app.post("/posters")
def posters():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("ids"), list):
        return jsonify({"error": "Provide a list of movie IDs."}), 400

    requested_ids = payload["ids"]
    if (
        not requested_ids
        or len(requested_ids) > 10
        or any(
            type(movie_id) is not int or movie_id not in movie_ids
            for movie_id in requested_ids
        )
    ):
        return jsonify({"error": "Provide up to 10 valid movie IDs from the catalogue."}), 400

    token = os.environ.get("TMDB_API_TOKEN", "").strip()
    if not token:
        return jsonify({"enabled": False, "posters": {}})

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(
            executor.map(
                lambda movie_id: get_movie_poster(movie_id, token),
                requested_ids,
            )
        )

    if any(error in {"auth", "network", "service"} for _, error in results):
        get_movie_poster.cache_clear()

    return jsonify(
        {
            "enabled": True,
            "posters": {
                str(movie_id): poster_url
                for movie_id, (poster_url, _) in zip(requested_ids, results)
                if poster_url
            },
            "errors": sorted(
                {error for _, error in results if error and error != "not_found"}
            ),
        }
    )


if __name__ == "__main__":
    app.run(debug=False)
