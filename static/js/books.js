const mobileBookLayout = window.matchMedia("(max-width: 768px)");
const bookCoverToggles = document.querySelectorAll(".book_cover_toggle");

bookCoverToggles.forEach((button) => {
    button.addEventListener("click", () => {
        if (!mobileBookLayout.matches) return;

        const isTilted = button.getAttribute("aria-pressed") === "true";
        button.setAttribute("aria-pressed", String(!isTilted));
    });
});

mobileBookLayout.addEventListener("change", () => {
    bookCoverToggles.forEach((button) => {
        button.setAttribute("aria-pressed", "false");
    });
});
