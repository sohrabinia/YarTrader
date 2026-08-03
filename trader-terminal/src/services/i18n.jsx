import React, { createContext, useContext, useState, useEffect } from 'react';
import { CONFIG } from '../core/config.js';

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('tradeyar_language') || 'fa');
  const [locales, setLocales] = useState({});
  const [loading, setLoading] = useState(true);

  const loadLocales = async (targetLang) => {
    try {
      const resp = await fetch(`${CONFIG.apiBaseUrl}/locales/${targetLang}.json`);
      if (!resp.ok) {
        throw new Error(`Failed to load locales: ${resp.status}`);
      }
      const data = await resp.json();
      setLocales(data);

      // Update body dir and styling exactly as in web_dashboard.py
      const isRTL = targetLang === 'fa' || targetLang === 'ar';
      document.body.dir = isRTL ? 'rtl' : 'ltr';
      document.body.style.fontFamily = isRTL ? "'Vazirmatn', sans-serif" : "'Segoe UI', Roboto, sans-serif";
      document.title = data['app_title'] || "TradeYar AI";
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLocales(lang);
  }, [lang]);

  const changeLanguage = (newLang) => {
    localStorage.setItem('tradeyar_language', newLang);
    setLang(newLang);
  };

  const t = (key) => locales[key] || key;

  return (
    <I18nContext.Provider value={{ lang, changeLanguage, t, locales, loading }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider');
  }
  return context;
}
