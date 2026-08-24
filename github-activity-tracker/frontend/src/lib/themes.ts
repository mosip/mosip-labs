export const THEME_STORAGE_KEY = "gat-theme";

export const THEMES = [
  { id: "sky", name: "Sky", swatch: "#4a90c8", scheme: "light" },
  { id: "teal", name: "Teal", swatch: "#0f4c4a", scheme: "light" },
  { id: "sunset", name: "Sunset", swatch: "#9a3412", scheme: "light" },
  { id: "forest", name: "Forest", swatch: "#14532d", scheme: "light" },
  { id: "violet", name: "Violet", swatch: "#5b21b6", scheme: "light" },
  { id: "graphite", name: "Graphite", swatch: "#1e293b", scheme: "light" },
  { id: "midnight", name: "Midnight", swatch: "#0b1220", scheme: "dark" },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeId = "sky";

export function isThemeId(value: string | null): value is ThemeId {
  return THEMES.some((theme) => theme.id === value);
}

export function getStoredTheme(): ThemeId {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (isThemeId(value)) return value;
  } catch {
    /* ignore private-mode storage errors */
  }
  return DEFAULT_THEME;
}

export function applyTheme(id: ThemeId) {
  const theme = THEMES.find((item) => item.id === id) ?? THEMES[0];
  document.documentElement.setAttribute("data-theme", theme.id);
  document.documentElement.style.colorScheme = theme.scheme;
}

export function persistTheme(id: ThemeId) {
  applyTheme(id);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, id);
  } catch {
    /* ignore private-mode storage errors */
  }
}
