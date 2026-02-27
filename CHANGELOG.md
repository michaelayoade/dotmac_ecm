# Changelog

All notable changes to dotmac_ecm are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-02-27

### Security

- [Security] Exclude `.env.agent-swarm` from version control to prevent live API credentials from being committed (PR #1)
- [Security] Fix audit log actor spoofing: actor identity now sourced from `request.state` instead of client-controlled HTTP headers `x-actor-type` / `x-actor-id` (PR #2)
- [Security] Fix webhook SSRF: `WebhookEndpointCreate.url` now rejects non-HTTP(S) schemes, loopback addresses, link-local ranges, and RFC 1918 private IP ranges using stdlib `ipaddress` + `urllib.parse` (PR #4)
- [Security] Fix refresh cookie `Secure` flag: `_refresh_cookie_secure()` now defaults to `True`; set `REFRESH_COOKIE_SECURE=false` to override for local development (PR #3)
- [Security] Add per-IP rate limiting to auth endpoints via slowapi/Redis: `POST /auth/login` 5/min, `POST /auth/forgot-password` 3/min, `POST /auth/mfa/verify` 5/min, `POST /auth/refresh` 10/min (PR #5)
