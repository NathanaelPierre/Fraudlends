import { useTranslation } from "react-i18next";
import { setLanguage } from "../i18n";

const LANGUAGES = [
  { code: "en", labelKey: "en" },
  { code: "fr", labelKey: "fr" },
  { code: "cr", labelKey: "cr" },
];

// A compact language picker — used in FolderNav's footer, next to the
// user's email, so it's reachable from every page without its own
// dedicated settings screen. Changing language here immediately
// affects: static UI text (via react-i18next) and every future API
// call to endpoints that accept ?language= (see api/client.js's
// getLanguage()/language-aware calls) — it does NOT retroactively
// re-translate a check result already on screen, since that content
// was generated server-side at submission time in whatever language
// the message itself was detected as.
export default function LanguageSwitcher({ collapsed }) {
  const { i18n, t } = useTranslation();

  function handleChange(e) {
    setLanguage(e.target.value);
  }

  if (collapsed) {
    return null;
  }

  return (
    <div className="language-switcher">
      <label htmlFor="language-select" className="hint">
        {t("languageSwitcher.label")}
      </label>
      <select id="language-select" value={i18n.language} onChange={handleChange}>
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {t(`languageSwitcher.${lang.labelKey}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
