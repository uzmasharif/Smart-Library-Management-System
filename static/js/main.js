
const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");

const moduleCards = document.querySelectorAll(".module-card");
const noResults = document.getElementById("noResults");

function searchModules() {

    const searchText = searchInput.value.toLowerCase().trim();

    let found = 0;

    moduleCards.forEach(function(card) {

        const cardText = card.innerText.toLowerCase();

        if (cardText.includes(searchText)) {

            card.style.display = "block";
            found++;

        } else {

            card.style.display = "none";

        }

    });

    noResults.hidden = found !== 0;

}

searchButton.addEventListener("click", searchModules);

searchInput.addEventListener("input", searchModules);
