
document.addEventListener("DOMContentLoaded", () => {
    console.log("Welcome! The Website is ready to recommend you some music.");

    const form = document.getElementById("music-form");
    const resultsDiv = document.getElementById("results");

    form.addEventListener("submit", async (event) => {
        event.preventDefault(); 

        // Get user inputs
        const genre = document.getElementById("genre").value;
        const artist = document.getElementById("artist").value;
        const mood = document.getElementById("mood").value;

        console.log(`Looking for songs in the genre "${genre}" by "${artist}" while feeling "${mood}".`);

        try {
            // Send data to the server
            const response = await fetch("/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ genre, artist, mood }),
            });

            const data = await response.json();
            resultsDiv.innerHTML = ""; // Clear old results

            if (data.error) {
                resultsDiv.innerHTML = `<p style="color: red;">${data.error}</p>`;
                console.warn("Server Error:", data.error);
                return;
            }

            // Display recommendations
            if (data.recommendations && data.recommendations.length > 0) {
                const list = document.createElement("ul");

                data.recommendations.forEach((song) => {
                    const listItem = document.createElement("li");
                    listItem.innerHTML = `
                        <strong>${song.title}</strong> by ${song.artist}
                        <a href="${song.link}" target="_blank">Listen on Spotify</a>
                    `;
                    list.appendChild(listItem);
                });

                resultsDiv.appendChild(list);
            } else {
                resultsDiv.innerHTML = "<p>No songs found. Maybe try different inputs?</p>";
            }
        } catch (error) {
            console.error("Something went wrong:", error);
            resultsDiv.innerHTML = `<p style="color: red;">Oops! Something went wrong. Please try again later.</p>`;
        }
    });
});