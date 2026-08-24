import React from "react";
import { THEMES } from "../lib/themes";
import { useTheme } from "../ThemeContext";

const ThemeSwitcher: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const current = THEMES.find((item) => item.id === theme) ?? THEMES[0];

  return (
    <div className="flex flex-col">
      <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
        Theme · {current.name}
      </label>
      <div className="flex items-center gap-2" role="radiogroup" aria-label="Color theme">
        {THEMES.map((item) => {
          const selected = item.id === theme;
          return (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={selected}
              title={item.name}
              onClick={() => setTheme(item.id)}
              className={`h-7 w-7 rounded-full border-2 transition ${
                selected
                  ? "border-white scale-110 shadow-lg"
                  : "border-white/35 hover:border-white/80"
              }`}
              style={{ backgroundColor: item.swatch }}
            />
          );
        })}
      </div>
    </div>
  );
};

export default ThemeSwitcher;
