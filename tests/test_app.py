import os
import unittest
from unittest.mock import Mock, patch

import app as app_module
import requests
from app import app, movies
from train_model import get_cast, get_director, get_names, parse_data


class RecommendationAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_lists_movie_suggestions(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Movie Discovery", response.data)
        self.assertIn(movies.iloc[0]["title"].encode(), response.data)

    def test_recommend_rejects_missing_or_invalid_title(self):
        for payload in ({}, {"movie": "  "}, {"movie": 123}):
            with self.subTest(payload=payload):
                response = self.client.post("/recommend", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_recommend_returns_similar_movies_case_insensitively(self):
        response = self.client.post("/recommend", json={"movie": "aVaTaR"})

        self.assertEqual(response.status_code, 200)
        recommendations = response.get_json()
        self.assertEqual(len(recommendations), 10)
        self.assertNotIn("Avatar", [item["title"] for item in recommendations])
        self.assertTrue(
            all(0 <= item["similarity"] <= 1 for item in recommendations)
        )
        self.assertTrue(all(isinstance(item["id"], int) for item in recommendations))
        self.assertEqual(
            [item["similarity"] for item in recommendations],
            sorted(
                (item["similarity"] for item in recommendations),
                reverse=True,
            ),
        )

    def test_recommend_returns_not_found_for_unknown_title(self):
        response = self.client.post(
            "/recommend", json={"movie": "A movie that is not in the dataset"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())

    def test_recommend_rejects_non_json_request(self):
        response = self.client.post("/recommend", data="movie=Avatar")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_posters_are_disabled_without_a_tmdb_token(self):
        movie_id = int(movies.iloc[0]["id"])
        with patch.dict(os.environ, {"TMDB_API_TOKEN": ""}):
            response = self.client.post("/posters", json={"ids": [movie_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"enabled": False, "posters": {}})

    def test_posters_lookup_uses_server_token_and_returns_tmdb_image_url(self):
        movie_id = int(movies.iloc[0]["id"])
        tmdb_response = Mock()
        tmdb_response.json.return_value = {"poster_path": "/poster.jpg"}
        app_module.get_movie_poster.cache_clear()

        with (
            patch.dict(os.environ, {"TMDB_API_TOKEN": "test-token"}),
            patch("app.requests.get", return_value=tmdb_response) as get,
        ):
            response = self.client.post("/posters", json={"ids": [movie_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "enabled": True,
                "posters": {
                    str(movie_id): "https://image.tmdb.org/t/p/w342/poster.jpg"
                },
                "errors": [],
            },
        )
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"], "Bearer test-token"
        )
        app_module.get_movie_poster.cache_clear()

    def test_posters_reject_invalid_or_unknown_ids(self):
        invalid_payloads = ({}, {"ids": []}, {"ids": [True]}, {"ids": [999999999]})

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/posters", json=payload)
                self.assertEqual(response.status_code, 400)

    def test_posters_ignore_unsafe_tmdb_paths(self):
        movie_id = int(movies.iloc[0]["id"])
        tmdb_response = Mock()
        tmdb_response.json.return_value = {"poster_path": "//example.com/poster.jpg"}
        app_module.get_movie_poster.cache_clear()

        with (
            patch.dict(os.environ, {"TMDB_API_TOKEN": "test-token"}),
            patch("app.requests.get", return_value=tmdb_response),
        ):
            response = self.client.post("/posters", json={"ids": [movie_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"enabled": True, "posters": {}, "errors": []},
        )
        app_module.get_movie_poster.cache_clear()

    def test_posters_report_invalid_token_without_returning_credentials(self):
        movie_id = int(movies.iloc[0]["id"])
        tmdb_response = Mock()
        tmdb_response.status_code = 401
        tmdb_response.raise_for_status.side_effect = requests.HTTPError(
            response=tmdb_response
        )
        app_module.get_movie_poster.cache_clear()

        with (
            patch.dict(os.environ, {"TMDB_API_TOKEN": "test-token"}),
            patch("app.requests.get", return_value=tmdb_response),
        ):
            response = self.client.post("/posters", json={"ids": [movie_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["errors"], ["auth"])
        self.assertNotIn("test-token", response.get_data(as_text=True))
        app_module.get_movie_poster.cache_clear()

    def test_posters_report_network_failures(self):
        movie_id = int(movies.iloc[0]["id"])
        app_module.get_movie_poster.cache_clear()

        with (
            patch.dict(os.environ, {"TMDB_API_TOKEN": "test-token"}),
            patch(
                "app.requests.get",
                side_effect=requests.ConnectionError("offline"),
            ),
        ):
            response = self.client.post("/posters", json={"ids": [movie_id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["errors"], ["network"])
        app_module.get_movie_poster.cache_clear()


class TrainingDataParsingTests(unittest.TestCase):
    def test_parse_data_handles_lists_and_invalid_values(self):
        self.assertEqual(parse_data('[{"name": "Drama"}]'), [{"name": "Drama"}])
        self.assertEqual(parse_data([{"name": "Drama"}]), [{"name": "Drama"}])
        self.assertEqual(parse_data("not valid data"), [])

    def test_feature_parsers_extract_names_and_director(self):
        self.assertEqual(
            get_names('[{"name": "Drama"}, {"name": "Adventure"}]'),
            ["Drama", "Adventure"],
        )
        self.assertEqual(
            get_cast('[{"name": "Actor One"}, {"name": "Actor Two"}, {"name": "Actor Three"}, {"name": "Actor Four"}]'),
            ["Actor One", "Actor Two", "Actor Three"],
        )
        self.assertEqual(
            get_director(
                '[{"name": "Actor One", "job": "Actor"}, '
                '{"name": "Director One", "job": "Director"}]'
            ),
            ["Director One"],
        )


if __name__ == "__main__":
    unittest.main()
