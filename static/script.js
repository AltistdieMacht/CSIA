document.addEventListener("DOMContentLoaded", () => {
    console.log("Script loaded and ready!");

    const form = document.getElementById("music-form");
    const resultsDiv = document.getElementById("results");

    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent form submission

        // Get user input
        const genre = document.getElementById("genre").value.trim();
        const artist = document.getElementById("artist").value.trim();

        // Validate input
        if (!genre || !artist) {
            alert("Please fill out both fields.");
            return;
        }

        try {
            // Send request to server
            const response = await fetch("/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ genre, artist }),
            });

            const data = await response.json();

            // Clear previous results
            resultsDiv.innerHTML = "";

            // Handle errors
            if (data.error) {
                resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            // Render recommendations
            data.recommendations.forEach((song) => {
                const card = document.createElement("div");
                card.className = "col-md-4 mb-4";
                card.innerHTML = `
                    <div class="card h-100">
                        <img src="${song.image || 'https://via.placeholder.com/150'}" class="card-img-top" alt="${song.title}">
                        <div class="card-body">
                            <h5 class="card-title">${song.title}</h5>
                            <p class="card-text">Artist: ${song.artist}</p>
                            <a href="${song.link}" class="btn btn-primary" target="_blank">Listen on Spotify</a>
                        </div>
                    </div>
                `;
                resultsDiv.appendChild(card);
            });
        } catch (error) {
            console.error("Error fetching recommendations:", error);
            resultsDiv.innerHTML = `<div class="alert alert-danger">Something went wrong. Please try again later.</div>`;
        }
    });
});
