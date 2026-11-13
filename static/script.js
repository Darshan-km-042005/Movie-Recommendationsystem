
async function getRecommendations() {
    const movie = document.getElementById("movie").value.trim();
    const results = document.getElementById("results");
    const heading = document.getElementById("heading");

    if (!movie) {
        alert("Please enter a movie name");
        return;
    }

    results.innerHTML = "Loading recommendations...";
    heading.innerText = "";

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ movie: movie })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Movie not found");
        }

        heading.innerText = "Recommended Movies";
        results.innerHTML = "";

        data.forEach(item => {
            const card = document.createElement("div");
            card.className = "movie-card";

            // Movie poster
            const poster = document.createElement("img");
            poster.className = "movie-poster";
            poster.alt = item.title + " poster";

            poster.src = item.poster ||
                "https://placehold.co/300x450/222230/ffffff?text=No+Poster";

            // Use placeholder if poster fails to load
            poster.onerror = function () {
                this.onerror = null;
                this.src =
                    "https://placehold.co/300x450/222230/ffffff?text=No+Poster";
            };

            // Movie title
            const title = document.createElement("h3");
            title.textContent = item.title;

            // Movie overview
            const overview = document.createElement("p");
            overview.textContent =
                item.overview || "No description available.";

            // Similarity score
            const score = document.createElement("p");
            score.className = "score";
            score.textContent = "Similarity: " + item.similarity;

            card.append(poster, title, overview, score);
            results.appendChild(card);
        });

    } catch (error) {
        results.textContent = error.message;
    }
}

function selectMovie(movieName) {
    document.getElementById("movie").value = movieName;
    getRecommendations();
}
