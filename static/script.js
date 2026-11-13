const searchForm = document.getElementById("search-form");
const movieInput = document.getElementById("movie");
const results = document.getElementById("results");
const statusMessage = document.getElementById("status");
const resultCount = document.getElementById("result-count");
const submitButton = document.getElementById("submit-button");
const heading = document.getElementById("heading");

searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    getRecommendations();
});

document.querySelectorAll(".pick").forEach((button) => {
    button.addEventListener("click", () => {
        movieInput.value = button.dataset.title;
        getRecommendations();
    });
});

async function getRecommendations() {
    const movie = movieInput.value.trim();
    statusMessage.classList.remove("status-error");
    if (!movie) {
        movieInput.focus();
        statusMessage.textContent = "Enter a movie title to get started.";
        return;
    }

    submitButton.disabled = true;
    submitButton.querySelector("span").textContent = "Finding...";
    heading.textContent = "Your next favorites";
    statusMessage.textContent = `Finding movies like “${movie}”…`;
    resultCount.textContent = "";
    results.replaceChildren();

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ movie }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong. Please try again.");
        }

        statusMessage.classList.remove("status-error");
        heading.textContent = `Because you watched ${movie}`;
        if (data.length === 0) {
            statusMessage.textContent = "We couldn't find similar movies for that title.";
            return;
        }

        statusMessage.textContent = "Movies with similar stories, genres, and creative talent.";
        resultCount.textContent = `${data.length} recommendations`;
        data.forEach((movieData, index) => results.appendChild(createMovieCard(movieData, index)));
        await loadPosters(data);
    } catch (error) {
        heading.textContent = "Your next favorites";
        statusMessage.textContent = error.message || "Unable to load recommendations. Please try again.";
        statusMessage.classList.add("status-error");
    } finally {
        submitButton.disabled = false;
        submitButton.querySelector("span").textContent = "Find movies";
    }
}

async function loadPosters(recommendations) {
    try {
        const response = await fetch("/posters", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: recommendations.map((movie) => movie.id) }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Unable to load movie posters.");
        }

        if (!data.enabled) {
            statusMessage.textContent =
                "Recommendations ready. Set TMDB_API_TOKEN to display movie posters.";
            return;
        }

        const posterErrors = data.errors || [];
        if (posterErrors.includes("auth")) {
            statusMessage.textContent =
                "TMDb rejected the API token. Use the API Read Access Token, check the TMDB_API_TOKEN setting, then restart the app.";
            statusMessage.classList.add("status-error");
        } else if (posterErrors.includes("network")) {
            statusMessage.textContent =
                "The app cannot connect to TMDb. Check your internet connection, firewall, or proxy settings.";
            statusMessage.classList.add("status-error");
        } else if (posterErrors.includes("service")) {
            statusMessage.textContent =
                "TMDb could not complete the poster lookup. Check the app terminal for details and try again.";
            statusMessage.classList.add("status-error");
        }

        if (Object.keys(data.posters).length === 0) {
            if (posterErrors.length === 0) {
                statusMessage.textContent =
                    "TMDb has no poster artwork for these recommendations.";
            }
            return;
        }

        if (
            Object.keys(data.posters).length < recommendations.length &&
            posterErrors.length === 0
        ) {
            statusMessage.textContent = "Some movies don’t have poster artwork available.";
        }

        let failedImages = 0;
        recommendations.forEach((movie) => {
            const posterUrl = data.posters[String(movie.id)];
            if (!posterUrl) {
                return;
            }

            const card = results.querySelector(`[data-movie-id="${movie.id}"]`);
            const image = card.querySelector(".movie-poster");
            image.addEventListener("load", () => card.classList.add("has-poster"), { once: true });
            image.addEventListener("error", () => {
                console.warn(`TMDb poster image failed to load for "${movie.title}".`);
                failedImages += 1;
                if (failedImages === 1) {
                    statusMessage.textContent =
                        "Poster details loaded, but the image server could not load the artwork. Check your internet connection.";
                    statusMessage.classList.add("status-error");
                }
            }, { once: true });
            image.src = posterUrl;
        });
    } catch (error) {
        console.warn("Could not load movie posters:", error);
        statusMessage.textContent = "Recommendations are ready, but movie posters could not be loaded.";
    }
}

function createMovieCard(movie, index) {
    const card = document.createElement("article");
    card.className = "movie-card";
    card.dataset.movieId = movie.id;

    const rank = document.createElement("span");
    rank.className = "movie-rank";
    rank.textContent = String(index + 1).padStart(2, "0");

    const posterFrame = document.createElement("div");
    posterFrame.className = "movie-poster-frame";

    const placeholder = document.createElement("span");
    placeholder.className = "poster-placeholder";
    placeholder.textContent = "POSTER ARTWORK";

    const image = document.createElement("img");
    image.className = "movie-poster";
    image.alt = `Poster for ${movie.title}`;
    image.loading = "lazy";
    image.decoding = "async";
    posterFrame.append(placeholder, image);

    const title = document.createElement("h3");
    title.textContent = movie.title;

    const overview = document.createElement("p");
    overview.className = "movie-overview";
    overview.textContent = movie.overview || "No synopsis is available for this film.";

    const match = document.createElement("div");
    match.className = "match-row";

    const matchLabel = document.createElement("span");
    matchLabel.textContent = "MATCH";

    const score = document.createElement("span");
    score.className = "match-score";
    score.textContent = `${Math.round(movie.similarity * 100)}%`;

    const track = document.createElement("div");
    track.className = "match-track";
    track.setAttribute("aria-label", `${score.textContent} similarity`);
    const fill = document.createElement("span");
    fill.style.width = `${Math.round(movie.similarity * 100)}%`;
    track.appendChild(fill);

    match.append(matchLabel, score);
    card.append(posterFrame, rank, title, overview, match, track);
    return card;
}
