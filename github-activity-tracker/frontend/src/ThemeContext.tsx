import React, { createContext, useContext, useMemo, useState } from "react";
import {
  applyTheme,
  getStoredTheme,
  persistTheme,
  type ThemeId,
} from "./lib/themes";

interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (id: ThemeId) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [theme, setThemeState] = useState<ThemeId>(() => {
    const stored = getStoredTheme();
    applyTheme(stored);
    return stored;
  });

  const value = useMemo(
    () => ({
      theme,
      setTheme: (id: ThemeId) => {
        persistTheme(id);
        setThemeState(id);
      },
    }),
    [theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
