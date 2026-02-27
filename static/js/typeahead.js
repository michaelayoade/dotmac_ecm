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

        // Unique ID prefix so multiple typeaheads on the same page don't clash
        var uid = "ta-" + Math.random().toString(36).slice(2, 8);
        var listboxId = uid + "-listbox";
        var timer = null;
        var lastQuery = "";
        var activeIndex = -1;

        // Wire up ARIA combobox attributes on the input
        input.setAttribute("role", "combobox");
        input.setAttribute("aria-autocomplete", "list");
        input.setAttribute("aria-expanded", "false");
        input.setAttribute("aria-haspopup", "listbox");
        input.setAttribute("aria-controls", listboxId);
        results.setAttribute("id", listboxId);

        function getOptions() {
            return results.querySelectorAll("[role='option']");
        }

        function setActiveOption(index) {
            var options = getOptions();
            options.forEach(function (opt, i) {
                if (i === index) {
                    opt.setAttribute("aria-selected", "true");
                    opt.classList.add("bg-slate-100", "dark:bg-slate-700");
                    input.setAttribute("aria-activedescendant", opt.id);
                } else {
                    opt.setAttribute("aria-selected", "false");
                    opt.classList.remove("bg-slate-100", "dark:bg-slate-700");
                }
            });
            activeIndex = index;
        }

        function clearResults() {
            results.innerHTML = "";
            activeIndex = -1;
            input.setAttribute("aria-expanded", "false");
            input.removeAttribute("aria-activedescendant");
        }

        function renderResults(items) {
            if (!items || !items.length) {
                clearResults();
                return;
            }
            var menu = document.createElement("div");
            menu.setAttribute("role", "listbox");
            menu.id = listboxId;
            menu.className = "absolute z-10 mt-2 w-full rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800";
            items.forEach(function (item, idx) {
                var optId = uid + "-opt-" + idx;
                var button = document.createElement("button");
                button.type = "button";
                button.id = optId;
                button.setAttribute("role", "option");
                button.setAttribute("aria-selected", "false");
                button.className = "w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700";
                button.textContent = item.label || item.name || "";
                button.addEventListener("click", function () {
                    input.value = item.label || item.name || "";
                    hidden.value = item.ref || item.id || "";
                    clearResults();
                    input.focus();
                });
                // Mouseenter keeps track of active highlight without changing focus
                button.addEventListener("mouseenter", function () {
                    setActiveOption(idx);
                });
                menu.appendChild(button);
            });
            results.innerHTML = "";
            results.appendChild(menu);
            input.setAttribute("aria-expanded", "true");
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

        // Keyboard navigation: ArrowDown / ArrowUp / Enter / Escape / Tab
        input.addEventListener("keydown", function (event) {
            var options = getOptions();
            var count = options.length;
            if (!count && event.key !== "Escape") {
                return;
            }
            switch (event.key) {
                case "ArrowDown":
                    event.preventDefault();
                    setActiveOption(activeIndex < count - 1 ? activeIndex + 1 : 0);
                    break;
                case "ArrowUp":
                    event.preventDefault();
                    setActiveOption(activeIndex > 0 ? activeIndex - 1 : count - 1);
                    break;
                case "Enter":
                    if (activeIndex >= 0 && activeIndex < count) {
                        event.preventDefault();
                        options[activeIndex].click();
                    }
                    break;
                case "Escape":
                case "Tab":
                    clearResults();
                    break;
            }
        });

        // Close when clicking outside the container
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
