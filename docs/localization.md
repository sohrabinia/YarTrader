# TradeYar AI Dashboard Localization System

The TradeYar AI dashboard features a robust, lightweight frontend translation system providing complete bilingual support (Persian / English) with dual-direction layout logic (RTL / LTR).

## Core Configurations

- **Supported Languages**: Persian (`fa-IR`, default) & English (`en-US`, fallback).
- **Default Language**: Persian (`fa`).
- **Translation File Structure**: Translations are loaded dynamically from:
  - `src/Application/Services/locales/fa.json`
  - `src/Application/Services/locales/en.json`

## Language Storage and Preference Persistence

The selected language is stored inside client browser's `localStorage` space under the key:
```javascript
tradeYar_language
```
If no preference is found, it automatically defaults to `fa`.

## Layout Dynamics (RTL/LTR switching)

Changing the selected language dynamically modifies the top level HTML attributes:
```html
<!-- Persian Mode (Default) -->
<html lang="fa" dir="rtl">

<!-- English Mode -->
<html lang="en" dir="ltr">
```

Styling rules optimized with logical directions (`[dir="rtl"]`) ensure correct margins, Vazirmatn font-face rendering, right-aligned tables, and customized status indicators for Persian readers.

## Localized Date Formatting

Timestamps render using the corresponding locale rules via JavaScript's native `Intl.DateTimeFormat`:
- **Persian**: `۱۴۰۵/۰۵/۰۷ ۱۳:۵۲` (using native Persian digits and dynamic RTL alignment).
- **English**: `2026-07-29 13:52` (using standard ISO structures).

## How to Add New Translations

1. Add your localizable UI elements with a `data-i18n` attribute pointing to a unique translation key:
   ```html
   <p data-i18n="my_custom_key">My English Text</p>
   ```
2. Update both locale JSON files under `src/Application/Services/locales/`:
   - `fa.json`: `"my_custom_key": "متن فارسی من"`
   - `en.json`: `"my_custom_key": "My English Text"`
3. If the translation requires dynamic runtime replacement, add matching string replacement inside `updateUI()` or local parsing routines.
