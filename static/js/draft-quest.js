function celebrateGoal() {
    const message = document.getElementById("goal_celebration");

    if (!message) {
        return;
    }

    // Keep the congratulations message, but skip motion when requested.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
    }

    const colors = ["#8f6b2f", "#d6c39d", "#e8b44f", "#628665", "#b97482"];
    const confettiLayer = document.createElement("div");

    confettiLayer.className = "confetti_layer";
    confettiLayer.setAttribute("aria-hidden", "true");
    document.body.appendChild(confettiLayer);

    for (let index = 0; index < 100; index++) {
        const piece = document.createElement("span");

        piece.className = "confetti_piece";
        piece.style.left = `${Math.random() * 100}%`;
        piece.style.backgroundColor =
            colors[Math.floor(Math.random() * colors.length)];

        piece.style.animationDuration = `${3 + Math.random() * 2}s`;
        piece.style.animationDelay = `${Math.random() * 0.8}s`;
        piece.style.setProperty(
            "--confetti_drift",
            `${Math.random() * 300 - 150}px`
        );

        confettiLayer.appendChild(piece);
    }

    // Remove the animation elements after all pieces have finished falling.
    window.setTimeout(() => {
        confettiLayer.remove();
    }, 6000);
}

celebrateGoal();