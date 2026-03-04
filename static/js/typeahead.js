(function () {
    function initTypeahead(container) {
        var input = container.querySelector("[data-typeahead-input]");
        var hidden = container.querySelector("[data-typeahead-hidden]");
        var results = container.querySelector("[data-typeahead-results]");
        var url = container.getAttribute("data-typeahead-url");
        var minChars = parseInt(container.getAttribute("data-typeahead-min") || "2", 10);
        var limit = parseInt(container.getAttribute("data-typeahead-limit") || "8", 10);
        if (!input || !hidden || !results || !url) {
            return;
        }
        var timer = null;
        var lastQuery = "";
        var activeIndex = -1;

        function getButtons() {
            var menu = results.querySelector("div");
            return menu ? Array.from(menu.querySelectorAll("button")) : [];
        }

        function setActive(index) {
            var buttons = getButtons();
            buttons.forEach(function (btn, i) {
                if (i === index) {
                    btn.classList.add("bg-slate-100", "dark:bg-slate-700");
                    btn.setAttribute("aria-selected", "true");
                } else {
                    btn.classList.remove("bg-slate-100", "dark:bg-slate-700");
                    btn.removeAttribute("aria-selected");
                }
            });
            activeIndex = index;
        }

        function clearResults() {
            results.innerHTML = "";
            activeIndex = -1;
        }

        function renderResults(items) {
            if (!items || !items.length) {
                clearResults();
                return;
            }
            var menu = document.createElement("div");
            menu.className = "absolute z-10 mt-2 w-full rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800";
            menu.setAttribute("role", "listbox");
            items.forEach(function (item, i) {
                var button = document.createElement("button");
                button.type = "button";
                button.setAttribute("role", "option");
                button.className = "w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700";
                button.textContent = item.label || item.name || "";
                button.addEventListener("click", function () {
                    input.value = item.label || item.name || "";
                    hidden.value = item.ref || item.id || "";
                    clearResults();
                });
                menu.appendChild(button);
            });
            results.innerHTML = "";
            results.appendChild(menu);
            activeIndex = -1;
        }

        function fetchResults(query) {
            var requestUrl = url + "?q=" + encodeURIComponent(query) + "&limit=" + limit;
            fetch(requestUrl)
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("typeahead request failed");
                    }
                    return response.json();
                })
                .then(function (data) {
                    renderResults((data && data.items) || []);
                })
                .catch(function () {
                    clearResults();
                });
        }

        input.addEventListener("input", function () {
            var query = input.value.trim();
            hidden.value = "";
            if (query.length < minChars) {
                clearResults();
                lastQuery = query;
                return;
            }
            if (timer) {
                window.clearTimeout(timer);
            }
            timer = window.setTimeout(function () {
                if (query !== lastQuery) {
                    fetchResults(query);
                    lastQuery = query;
                }
            }, 250);
        });

        input.addEventListener("keydown", function (event) {
            var buttons = getButtons();
            if (!buttons.length) {
                return;
            }
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive(activeIndex < buttons.length - 1 ? activeIndex + 1 : 0);
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive(activeIndex > 0 ? activeIndex - 1 : buttons.length - 1);
            } else if (event.key === "Enter") {
                event.preventDefault();
                if (activeIndex >= 0 && activeIndex < buttons.length) {
                    buttons[activeIndex].click();
                }
            } else if (event.key === "Escape") {
                clearResults();
            }
        });

        document.addEventListener("click", function (event) {
            if (!container.contains(event.target)) {
                clearResults();
            }
        });
    }

    function initAll() {
        var containers = document.querySelectorAll("[data-typeahead-url]");
        containers.forEach(function (container) {
            initTypeahead(container);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }
})();
