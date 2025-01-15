document.addEventListener("DOMContentLoaded", () => {
    console.log("Music Recommendation App loaded successfully!");

    const form = document.getElementById("music-form");

    // Event listener for form submission
    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent the default form submission

        // Collect user input
        const genre = document.getElementById("genre").value.trim();
        const artist = document.getElementById("artist").value.trim();
        const mood = document.getElementById("mood").value.trim();

        // Validate input
        if (!genre || !artist || !mood) {
            alert("Please fill out all fields: Genre, Artist, and Mood.");
            return;
        }

        console.log(`Form submitted with -> Genre: ${genre}, Artist: ${artist}, Mood: ${mood}`);

        try {
            // Send the form data to the server
            const response = await fetch("/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ genre, artist, mood }),
            });

            // Check if the response is successful
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }

            // Render the server response
            const html = await response.text();
            document.body.innerHTML = html;

        } catch (error) {
            console.error("Error occurred:", error);
            alert("An error occurred while processing your request. Please try again later.");
        }
    });
});
