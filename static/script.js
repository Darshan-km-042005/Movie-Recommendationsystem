
async function getRecommendations() {

    const movie = document.getElementById("movie").value;

    const results = document.getElementById("results");
    const heading = document.getElementById("heading");

    if (!movie.trim()) {
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

            body: JSON.stringify({
                movie: movie
            })
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

            const title = document.createElement("h3");
            title.textContent = item.title;

            const overview = document.createElement("p");
            overview.textContent =
                item.overview || "No description available.";

            const score = document.createElement("p");
            score.className = "score";
            score.textContent =
                "Similarity: " + item.similarity;

            card.append(title, overview, score);

            results.appendChild(card);

        });

    } catch (error) {

        results.textContent = error.message;

    }
}
