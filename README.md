# ReelGood — Movie Recommendation System

A content-based movie recommender built with Python, Flask, and scikit-learn. Enter a movie title and ReelGood finds up to ten related films using their genres, keywords, cast, director, and synopsis.

When configured with a TMDB API read access token, the app also displays official movie poster artwork. Recommendations continue to work without a token and show an artwork placeholder instead.

## How it works

1. `train_model.py` combines the bundled TMDB 5000 movies and credits datasets and extracts useful movie features.
2. `TfidfVectorizer` turns those features into TF-IDF vectors.
3. The Flask app compares a selected movie to the catalogue with cosine similarity and returns the closest matches.

The project includes the trained model at `model/recommender.joblib`, so you can run the web app without training it again.

## Requirements

- Python 3.10 or later
- The CSV files in `dataset/` (included)

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the app

From the project directory:

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. Use the suggestions or enter a movie title from the catalogue.

## Enable movie posters

1. Create a TMDB account and request an API read access token in your account's API settings.
2. Add the token to a `.env` file in the project root (the file is ignored by Git):

```env
TMDB_API_TOKEN=your-tmdb-read-access-token
```

The app loads `.env` automatically when started with `python app.py`. Do not commit the file or share the token publicly. Alternatively, set `TMDB_API_TOKEN` in the environment before launching the app.

PowerShell:

```powershell
$env:TMDB_API_TOKEN = "your-tmdb-read-access-token"
python app.py
```

macOS/Linux:

```bash
export TMDB_API_TOKEN="your-tmdb-read-access-token"
python app.py
```

The server uses the token to look up poster paths; it is never sent to the browser. Poster images are served by TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.

## Retrain the model

After updating either dataset, rebuild the model:

```bash
python train_model.py
```

The script writes the trained artifact to `model/recommender.joblib`. Both dataset files must be present in `dataset/`.

## Run tests

```bash
python -m unittest discover -s tests -v
```
