
import pandas as pd
import ast
import os
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer

# Load datasets
movies = pd.read_csv("dataset/tmdb_5000_movies.csv")
credits = pd.read_csv("dataset/tmdb_5000_credits.csv")

print("Datasets loaded successfully!")

# Merge datasets
credits = credits.rename(columns={"movie_id": "id"})
data = movies.merge(credits, on="id")

# Extract names from JSON data
def parse_data(value):
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return []

def get_names(items):
    return [
        item["name"]
        for item in parse_data(items)
        if isinstance(item, dict) and "name" in item
    ]

def get_cast(items):
    return get_names(str(parse_data(items)[:3]))

def get_director(items):
    for person in parse_data(items):
        if person.get("job") == "Director":
            return [person["name"]]
    return []

# Process movie information
data["genres"] = data["genres"].apply(get_names)
data["keywords"] = data["keywords"].apply(get_names)
data["cast"] = data["cast"].apply(get_cast)
data["crew"] = data["crew"].apply(get_director)

data["overview"] = data["overview"].fillna("")

# Combine features
data["tags"] = data.apply(
    lambda row: " ".join(
        row["genres"]
        + row["keywords"]
        + row["cast"]
        + row["crew"]
        + row["overview"].split()
    ),
    axis=1
)

# Select required columns
data = data[
    ["id", "title_x", "overview", "tags"]
]

data = data.rename(columns={"title_x": "title"})
data = data.dropna(subset=["title"])
data = data.drop_duplicates(subset=["title"])
data = data.reset_index(drop=True)

print("Movie data processed successfully!")

# TF-IDF vectorization
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=20000,
    ngram_range=(1, 2)
)

matrix = vectorizer.fit_transform(data["tags"])

print("Machine Learning model trained successfully!")

# Save trained model
os.makedirs("model", exist_ok=True)

joblib.dump(
    {
        "movies": data,
        "vectorizer": vectorizer,
        "matrix": matrix
    },
    "model/recommender.joblib",
    compress=3
)

print("Model saved successfully!")
print("Total movies:", len(data))
