import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Locale = "fr" | "en";

const STORAGE_KEY = "organchip.locale";

const messages = {
  fr: {
    "language.label": "Langue de l’interface",
    "language.fr": "Français",
    "language.en": "English",
  },
  en: {
    "language.label": "Interface language",
    "language.fr": "Français",
    "language.en": "English",
  },
} as const;

export type TranslationKey = keyof typeof messages.fr;

interface I18nContextValue {
  locale: Locale;
  localeTag: "fr-FR" | "en-US";
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function initialLocale(): Locale {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  const locale = stored === "en" || stored === "fr" ? stored : "fr";
  document.documentElement.lang = locale;
  return locale;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(initialLocale);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nContextValue>(() => ({
    locale,
    localeTag: locale === "fr" ? "fr-FR" : "en-US",
    setLocale,
    t: (key) => messages[locale][key],
  }), [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}
