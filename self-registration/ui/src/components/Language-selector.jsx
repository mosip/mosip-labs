import { useEffect } from "react";
import { useTranslation } from "react-i18next";

const languages = [
  { code: "en", lang: "English", dir: "ltr" },
  { code: "fr", lang: "Français", dir: "ltr" },
  { code: "es", lang: "Español - Próximamente", dir: "ltr" }
];

const LanguageSelector = () => {
  const { i18n } = useTranslation();

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    const selectedLang = languages.find((lang) => lang.code === lng);
    document.documentElement.setAttribute("dir", selectedLang?.dir || "ltr");
  };

  useEffect(() => {
    const currentLang = i18n.language;
    const selectedLang = languages.find((lang) => lang.code === currentLang);
    document.documentElement.setAttribute("dir", selectedLang?.dir || "ltr");
  }, [i18n.language]);

  return (
    <div className="absolute right-0 mt-2 w-32 md:w-max bg-white border border-gray-200 rounded-lg shadow-lg">
      {languages.map((language) => (
        <div
          key={language.code}
          onClick={() => language.code !== 'es' && changeLanguage(language.code)}
          className={`px-4 py-2 ${
            language.code === 'es' 
              ? 'text-gray-400 cursor-not-allowed' 
              : 'text-gray-700 hover:bg-gray-100 cursor-pointer'
          }`}
        >
          {language.lang}
        </div>
      ))}
    </div>
  );
};

export default LanguageSelector;