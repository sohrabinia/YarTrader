# YarTrader V6 Final Acceptance Gate — Baseline Reality Report

**Date:** August 19, 2026
**Status:** RECORDED
**Gatekeeper:** Senior Frontend Engineer & SRE Release Gatekeeper

---

## 1. Fresh Git State

- **Branch Name:** `jules-9636665624931956698-bbefc700`
- **HEAD Commit Hash:** `5d5bff5d1163def6208eaca9740e2ee02ab3d85c`
- **Working Tree Status:** Clean source files (untracked screenshot updates under `validation/frontend_v6_final/`)

---

## 2. Calculated Source & Locale Object Hashes

| Target File | Object Type | Calculated SHA-1 Blob Hash |
| :--- | :--- | :--- |
| `trader-terminal/src/App.jsx` | Source | `b8e071fe531c9e63784a0c51bd15d1705bbca820` |
| `trader-terminal/src/assets/globals.css` | Design Tokens | `54ff61a9b0fbf886fe0ed07fa6c6da61625eaa0e` |
| `trader-terminal/public/locales/fa.json` | Locale (Persian) | `e16eb8bea37aa71183e84ef79da4e8ab912814a1` |
| `trader-terminal/public/locales/en.json` | Locale (English) | `798190df310adc14f57106cbe9d06e3597422f45` |
| `trader-terminal/public/locales/tr.json` | Locale (Turkish) | `77ad462f209052dbd06e82daa441776a906805de` |
| `trader-terminal/public/locales/ar.json` | Locale (Arabic) | `2d151c13c65eeb9bca843de19fa5a35467f62328` |

---

## 3. Initial Locale Key Audit

- `fa.json`: 161 keys
- `en.json`: 161 keys
- `tr.json`: 156 keys (missing 5 keys: `nav_execution_intel`, `live_mode`, `demo_mode`, `checking_mode`, `unreachable_mode`)
- `ar.json`: 156 keys (missing 5 keys: `nav_execution_intel`, `live_mode`, `demo_mode`, `checking_mode`, `unreachable_mode`)

---

## 4. Certification

This baseline state was recorded directly from the live filesystem using `git status`, `git branch`, `git rev-parse`, and `git hash-object`. No assumed or historical report hashes were trusted.
