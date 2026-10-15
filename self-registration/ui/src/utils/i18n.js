import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

// Import translation files
import en from "../locales/english.json";
import es from "../locales/spanish.json";
import fr from "../locales/french.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    // debug: true,
    resources: {
      en: {
        translation: en,
      },
      es: {
        translation: es,
      },
      fr: {
        translation: fr,
      },
    },
    lng: "en", // Default language
    fallbackLng: "en", // Fallback language
    interpolation: { escapeValue: false },
  });

export default i18n;
