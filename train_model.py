import ast
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = Path(__file__).resolve().parent
MOVIES_PATH = BASE_DIR / "dataset" / "tmdb_5000_movies.csv"
CREDITS_PATH = BASE_DIR / "dataset" / "tmdb_5000_credits.csv"
MODEL_PATH = BASE_DIR / "model" / "recommender.joblib"


def parse_data(value):
    if isinstance(value, list):
        return value
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def get_names(items):
    return [
        item["name"]
        for item in parse_data(items)
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]


def get_cast(items):
    return get_names(parse_data(items)[:3])


def get_director(items):
    for person in parse_data(items):
        if isinstance(person, dict) and person.get("job") == "Director":
            name = person.get("name")
            return [name] if isinstance(name, str) else []
    return []


def main():
    if not MOVIES_PATH.is_file() or not CREDITS_PATH.is_file():
        raise FileNotFoundError(
            "TMDB movie and credits CSV files must both be present in the dataset folder."
        )

    movies = pd.read_csv(MOVIES_PATH)
    credits = pd.read_csv(CREDITS_PATH).rename(columns={"movie_id": "id"})
    data = movies.merge(credits, on="id")

    data["genres"] = data["genres"].apply(get_names)
    data["keywords"] = data["keywords"].apply(get_names)
    data["cast"] = data["cast"].apply(get_cast)
    data["crew"] = data["crew"].apply(get_director)
    data["overview"] = data["overview"].fillna("")
    data["tags"] = data.apply(
        lambda row: " ".join(
            row["genres"]
            + row["keywords"]
            + row["cast"]
            + row["crew"]
            + row["overview"].split()
        ),
        axis=1,
    )

    data = data[["id", "title_x", "overview", "tags"]]
    data = data.rename(columns={"title_x": "title"})
    data = data.dropna(subset=["title"]).drop_duplicates(subset=["title"])
    data = data.reset_index(drop=True)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=20000,
        ngram_range=(1, 2),
    )
    matrix = vectorizer.fit_transform(data["tags"])

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"movies": data, "vectorizer": vectorizer, "matrix": matrix},
        MODEL_PATH,
        compress=3,
    )
    print(f"Model saved to {MODEL_PATH}")
    print(f"Movies indexed: {len(data)}")


if __name__ == "__main__":
    main()
