# UI/UX Audit — Wave 1

**Date:** 2026-03-04
**Scope:** Server-rendered dashboard (`base.html`, `index.html`, `typeahead.js`, `avatar.js`)
**Stack:** Jinja2 + HTMX 2.0 + Alpine.js 3.x + Tailwind CSS (CDN)

---

## P0 — Critical

| # | Issue | Impact |
|---|-------|--------|
| 1 | **No dark-mode toggle in the UI.** System preference is detected on first visit, but users have no visible control to switch modes. The Alpine.js `darkMode` reactive state exists on `<html>` but nothing binds to it. | Users stuck in wrong theme; dark-mode code is dead weight. |
| 2 | **No skip-to-content link.** Screen-reader and keyboard users must tab through the full header on every page load. WCAG 2.1 SC 2.4.1 failure. | Accessibility blocker. |
| 3 | **Hardcoded counter `x-data="{ count: 214 }"`.** The "Active people" stat is a fake number with a dummy "Add person" button that only increments the counter client-side. Misleading to every visitor. | Erodes trust; confusing UX. |

## P1 — High

| # | Issue | Impact |
|---|-------|--------|
| 4 | **Typeahead has no keyboard navigation.** Arrow-key, Enter, and Escape are unhandled. Mouse-only interaction. | Accessibility gap; power-user friction. |
| 5 | **Mismatched feature-card icons.** "Settings hub" uses a mail/envelope icon; "Scheduled tasks" uses a map-pin icon. Neither conveys the feature described. | Visual confusion; looks unfinished. |
| 6 | **People list has no empty-state CTA that works.** The "Add your first person" link points to `/api/v1/people` (a JSON endpoint), not a usable form. | Dead-end link for non-developer users. |
| 7 | **No favicon.** Browser tabs show a generic icon. | Polish gap; brand recognition. |

## P2 — Medium

| # | Issue | Impact |
|---|-------|--------|
| 8 | **No `<meta name="description">`.** Missing SEO/social metadata. | Minor for internal tool; matters if public-facing. |
| 9 | **CDN-only dependencies (Tailwind, HTMX, Alpine).** No fallback or self-hosted option. | Single point of failure on CDN outage. |
| 10 | **Toast container is `pointer-events-none` on parent but `pointer-events-auto` on children.** Works, but the dismiss button's hit target is small (16 x 16 px). | Hard to dismiss on mobile. |
| 11 | **No loading skeleton for people list.** HTMX request returns full HTML, but initial server-render can be slow with many records. | Perceived performance on large datasets. |

---

## Wave 1 — Implemented Improvements

The following top-5 items are addressed in this branch:

1. **Dark-mode toggle button** (P0 #1) — sun/moon icon in header with Alpine.js binding.
2. **Skip-to-content link** (P0 #2) — visually hidden, keyboard-focusable anchor.
3. **Live people count** (P0 #3) — pass actual count from backend; remove fake counter button.
4. **Typeahead keyboard navigation** (P1 #4) — ArrowDown/Up, Enter to select, Escape to close.
5. **Fix mismatched icons** (P1 #5) — gear/cog for Settings hub, clock for Scheduled tasks.
