# Movie Recommendation System

A Flask web app that recommends movies with similar genres, keywords, cast, directors, and overviews using TF-IDF and cosine similarity.

## Requirements

- Python 3
- The TMDB 5000 movies and credits CSV files in `dataset/`

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

For movie posters, create a `.env` file in the project directory and add your TMDB read access token:

```env
TMDB_READ_ACCESS_TOKEN=your_tmdb_read_access_token
```

Posters are optional; the app works without a token.

Start the app from the project directory:

```bash
python app.py
```

Open the local address printed by Flask in your browser. The pre-trained model is included at `model/recommender.joblib`.

To rebuild the model after changing the datasets, run:

```bash
python train_model.py
```
