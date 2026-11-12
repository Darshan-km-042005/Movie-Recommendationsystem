
from flask import Flask, render_template, request, jsonify
import joblib
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Load trained ML model
model = joblib.load("model/recommender.joblib")

movies = model["movies"]
matrix = model["matrix"]

@app.route("/")
def home():
    movie_titles = movies["title"].tolist()
    return render_template("index.html", movies=movie_titles)


@app.route("/recommend", methods=["POST"])
def recommend():

    selected_movie = request.json.get("movie", "").strip()

    matches = movies[
        movies["title"].str.lower() == selected_movie.lower()
    ]

    if matches.empty:
        return jsonify({"error": "Movie not found"}), 404

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

        recommendations.append({
            "title": movie["title"],
            "overview": movie["overview"],
            "similarity": round(float(scores[index]), 3)
        })

        if len(recommendations) == 10:
            break

    return jsonify(recommendations)


if __name__ == "__main__":
    app.run(debug=True)
