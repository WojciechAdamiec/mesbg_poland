(function () {
    var HEADER_OFFSET = 110;
    var frame = null;

    function isVisible(element) {
        return element.getClientRects().length > 0;
    }

    function updateActive() {
        frame = null;
        var sections = document.querySelectorAll(".article-section");
        var links = document.querySelectorAll(".article-tracker-link");
        if (!sections.length || !links.length) {
            return;
        }
        var active = null;
        sections.forEach(function (section) {
            // Sections inside a collapsed parent are not rendered and cannot be read.
            if (isVisible(section) && section.getBoundingClientRect().top <= HEADER_OFFSET) {
                active = section;
            }
        });
        if (active === null) {
            active = sections[0];
        }
        var parents = {};
        var parent = active.parentElement && active.parentElement.closest(".article-section");
        while (parent) {
            parents[parent.id] = true;
            parent = parent.parentElement && parent.parentElement.closest(".article-section");
        }
        links.forEach(function (link) {
            link.classList.toggle("active", link.dataset.target === active.id);
            link.classList.toggle("active-parent", Boolean(parents[link.dataset.target]));
        });
    }

    function scheduleUpdate() {
        if (frame === null) {
            frame = window.requestAnimationFrame(updateActive);
        }
    }

    function setCollapsed(section, collapsed) {
        section.classList.toggle("collapsed", collapsed);
        var toggle = section.querySelector(":scope > .article-section-header > .article-toggle");
        if (toggle) {
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }
    }

    document.addEventListener("click", function (event) {
        var toggle = event.target.closest(".article-toggle");
        if (toggle) {
            var section = toggle.closest(".article-section");
            setCollapsed(section, !section.classList.contains("collapsed"));
            scheduleUpdate();
            return;
        }
        var link = event.target.closest(".article-tracker-link");
        if (link) {
            event.preventDefault();
            var target = document.getElementById(link.dataset.target);
            if (target) {
                // Reveal the section if it, or any section containing it, is hidden.
                var ancestor = target.parentElement && target.parentElement.closest(".article-section");
                while (ancestor) {
                    setCollapsed(ancestor, false);
                    ancestor = ancestor.parentElement && ancestor.parentElement.closest(".article-section");
                }
                setCollapsed(target, false);
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        }
    });

    // Capture phase, because the scrolling element depends on the layout.
    document.addEventListener("scroll", scheduleUpdate, true);
    window.addEventListener("resize", scheduleUpdate);
    // Dash renders pages after load, so watch for new sections.
    new MutationObserver(scheduleUpdate).observe(document.documentElement, { childList: true, subtree: true });
})();
