import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

const I18nContext = createContext(null);
const SUPPORTED_LANGS = ['fa', 'en', 'ar', 'tr'];
const RTL_LANGS = new Set(['fa', 'ar']);
const DEFAULT_LANG = 'fa';

function normalizeLang(value) {
  return SUPPORTED_LANGS.includes(value) ? value : DEFAULT_LANG;
}

function interpolate(value, params = {}) {
  if (typeof value !== 'string') return value;
  return value.replace(/{{\\s*([^}]+?)\\s*}}|{\\s*([^}]+?)\\s*}/g, (_, a, b) => {
    const key = (a || b || '').trim();
    return Object.prototype.hasOwnProperty.call(params, key) ? String(params[key]) : _;
  });
}

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => normalizeLang(localStorage.getItem('yartrader_language')));
  const [locales, setLocales] = useState({});
  const [fallbackLocales, setFallbackLocales] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetch('/locales/en.json').then(r => { if (!r.ok) throw new Error('English locale unavailable'); return r.json(); }),
      fetch('/locales/' + lang + '.json').then(r => { if (!r.ok) throw new Error(lang + ' locale unavailable'); return r.json(); })
    ]).then(([en, selected]) => {
      if (cancelled) return;
      setFallbackLocales(en);
      setLocales(selected);
    }).catch(error => {
      console.error('[YarTrader i18n]', error);
      if (!cancelled) {
        setFallbackLocales({});
        setLocales({});
      }
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [lang]);

  useEffect(() => {
    const rtl = RTL_LANGS.has(lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = rtl ? 'rtl' : 'ltr';
    document.body.dir = rtl ? 'rtl' : 'ltr';
    document.body.classList.toggle('rtl-layout', rtl);
    document.body.classList.toggle('ltr-layout', !rtl);
    document.body.style.fontFamily = rtl
      ? "'Vazirmatn', 'Segoe UI', sans-serif"
      : "Inter, 'Segoe UI', Roboto, sans-serif";
  }, [lang]);

  const changeLanguage = (next) => {
    const normalized = normalizeLang(next);
    localStorage.setItem('yartrader_language', normalized);
    setLang(normalized);
  };

  const t = useMemo(() => (key, params) => {
    const value = locales[key] ?? fallbackLocales[key] ?? key;
    return interpolate(value, params);
  }, [locales, fallbackLocales]);

  return (
    <I18nContext.Provider value={{ lang, changeLanguage, t, locales, loading, supportedLanguages: SUPPORTED_LANGS, isRTL: RTL_LANGS.has(lang) }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useTranslation must be used within I18nProvider');
  return context;
}

export const supportedLanguages = SUPPORTED_LANGS;
