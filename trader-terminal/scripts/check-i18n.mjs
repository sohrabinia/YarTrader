import fs from 'node:fs';

const languages = ['fa', 'en', 'ar', 'tr'];
const locale = Object.fromEntries(languages.map(lang => [lang, JSON.parse(fs.readFileSync(new URL('../public/locales/' + lang + '.json', import.meta.url), 'utf8'))]));
const baseKeys = new Set(Object.keys(locale.en));
const errors = [];

for (const lang of languages) {
  const keys = new Set(Object.keys(locale[lang]));
  for (const key of baseKeys) if (!keys.has(key)) errors.push(lang + ': missing key ' + key);
  for (const key of keys) if (!baseKeys.has(key)) errors.push(lang + ': unexpected key ' + key);
}

const placeholders = value => [...String(value).matchAll(/{{\s*([^}]+?)\s*}}|{\s*([^}]+?)\s*}/g)].map(m => (m[1] || m[2]).trim()).sort().join('|');
for (const key of baseKeys) {
  const expected = placeholders(locale.en[key]);
  for (const lang of languages) {
    if (placeholders(locale[lang][key]) !== expected) errors.push(lang + ': placeholder mismatch for ' + key);
  }
}

const interpolate = (value, params) => String(value).replace(/{{\s*([^}]+?)\s*}}|{\s*([^}]+?)\s*}/g, (match, a, b) => {
  const key = (a || b || '').trim();
  return Object.prototype.hasOwnProperty.call(params, key) ? String(params[key]) : match;
});
if (interpolate(locale.en.welcome_title, { version: '7.0' }) !== 'Welcome to YarTrader v7.0') {
  errors.push('runtime interpolation failed for welcome_title');
}
if (interpolate(locale.en.pricing_plan_limits, { symbols: 2, timeframes: 'M15, H1' }) !== 'Max Active Symbols: 2 | Timeframes: M15, H1') {
  errors.push('runtime interpolation failed for pricing_plan_limits');
}

if (errors.length) {
  console.error(errors.join('\\n'));
  process.exit(1);
}
console.log('i18n parity OK: ' + languages.join(', ') + ' — ' + baseKeys.size + ' keys; placeholder sets match.');
