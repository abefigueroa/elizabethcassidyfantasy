let weekRequest;

document.addEventListener("click", async (event) => {
    const link = event.target.closest(".week_navigation a");

    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        return;
    }

    event.preventDefault();
    weekRequest?.abort();
    const controller = new AbortController();
    weekRequest = controller;
    const panel = document.getElementById("weekly-words");
    const label = link.getAttribute("aria-label");
    panel.setAttribute("aria-busy", "true");

    try {
        const response = await fetch(link.href, { signal: controller.signal });
        if (!response.ok || response.redirected) {
            window.location.assign(response.redirected ? response.url : link.href);
            return;
        }

        const documentCopy = new DOMParser().parseFromString(await response.text(), "text/html");
        const updatedPanel = documentCopy.getElementById("weekly-words");
        if (!updatedPanel) {
            throw new Error("Weekly chart missing from response");
        }
        if (controller.signal.aborted) {
            return;
        }

        const { scrollX, scrollY } = window;
        panel.replaceWith(updatedPanel);
        const nextFocus = updatedPanel.querySelector(`[aria-label="${label}"]`)
            || updatedPanel.querySelector(".week_navigation a");
        nextFocus?.focus({ preventScroll: true });
        window.scrollTo({ left: scrollX, top: scrollY, behavior: "instant" });

        const url = new URL(link.href);
        url.hash = "";
        window.history.replaceState(null, "", url);
    } catch (error) {
        if (error.name !== "AbortError") {
            window.location.assign(link.href);
        }
    } finally {
        if (weekRequest === controller) {
            document.getElementById("weekly-words")?.removeAttribute("aria-busy");
        }
    }
});
