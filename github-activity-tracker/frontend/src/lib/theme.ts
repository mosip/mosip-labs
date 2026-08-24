/** Read a color token from `theme.css`. Used where Canvas/Chart.js need a real color string. */
export function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

export function chartTheme() {
  return {
    prs: cssVar("--color-pr", "#0EA5E9"),
    reviews: cssVar("--color-review", "#EA580C"),
    issues: cssVar("--color-issue", "#4F46E5"),
    legend: cssVar("--color-chart-legend", "#334155"),
    tick: cssVar("--color-chart-tick", "#64748b"),
    grid: cssVar("--color-chart-grid", "rgba(28, 25, 23, 0.12)"),
    hover: cssVar("--color-chart-hover", "rgba(250, 204, 21, 0.18)"),
    tooltipBg: cssVar("--color-chart-tooltip-bg", "rgba(255, 255, 255, 0.98)"),
    tooltipBorder: cssVar("--color-chart-tooltip-border", "rgba(196, 149, 110, 0.45)"),
    title: cssVar("--color-chart-title", "#0f172a"),
    up: cssVar("--color-up", "#0EA5E9"),
    down: cssVar("--color-down", "#E11D48"),
    neutral: cssVar("--color-neutral", "#EA580C"),
  };
}
