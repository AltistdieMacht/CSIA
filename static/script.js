// Ensure the script runs only after the page is fully loaded
document.addEventListener("DOMContentLoaded", () => {
    console.log("The website is ready to recommend some music!");

    // Grab the form and the results container
    const form = document.getElementById("music-form");
    const resultsDiv = document.getElementById("results");

    // Event listener for form submission
    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent the page from reloading

        // Get user inputs
        const genre = document.getElementById("genre").value.trim();
        const artist = document.getElementById("artist").value.trim();
        const mood = document.getElementById("mood").value.trim();

        // Clear previous results
        resultsDiv.innerHTML = "";

        // Log user inputs for debugging
        console.log(`Searching for songs with genre: "${genre}", artist: "${artist}", mood: "${mood}".`);

        try {
            // Send data to the server
            const response = await fetch("/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ genre, artist, mood }),
            });

            // Handle the server's response
            const data = await response.json();

            // Check if there is an error in the response
            if (data.error) {
                resultsDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
                console.error("Server Error:", data.error);
                return;
            }

            // Check if recommendations exist
            if (data.recommendations && data.recommendations.length > 0) {
                const list = document.createElement("ul");
                list.classList.add("list-group");

                data.recommendations.forEach((song) => {
                    const listItem = document.createElement("li");
                    listItem.classList.add("list-group-item", "d-flex", "justify-content-between", "align-items-center");

                    listItem.innerHTML = `
                        <div>
                            <strong>${song.title}</strong> by ${song.artist}
                        </div>
                        <a href="${song.link}" target="_blank" class="btn btn-success btn-sm">Listen on Spotify</a>
                    `;
                    list.appendChild(listItem);
                });

                resultsDiv.appendChild(list);
            } else {
                // If no recommendations are found
                resultsDiv.innerHTML = "<p>No songs found. Please try different inputs.</p>";
            }
        } catch (error) {
            // Handle unexpected errors
            console.error("Something went wrong:", error);
            resultsDiv.innerHTML = `<p style="color: red;">Oops! Something went wrong. Please try again later.</p>`;
        }
    });
});
