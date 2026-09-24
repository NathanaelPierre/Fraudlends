import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import fr from "./locales/fr.json";
import cr from "./locales/cr.json";

// Persisted so a returning user keeps their language choice across
// sessions, not just page loads within one — read once at init time,
// written whenever the user changes it (see LanguageSwitcher.jsx).
const STORAGE_KEY = "klaro_language";
const savedLanguage = localStorage.getItem(STORAGE_KEY);

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
    cr: { translation: cr },
  },
  lng: savedLanguage || "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false, // React already escapes output, i18next's own escaping would double-escape
  },
});

export function setLanguage(language) {
  i18n.changeLanguage(language);
  localStorage.setItem(STORAGE_KEY, language);
}

export default i18n;
