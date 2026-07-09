export const PERIOD_OPTIONS = [
  { value: "weekly", label: "Week" },
  { value: "monthly", label: "Month" },
  { value: "yearly", label: "Year" },
] as const;

export type PeriodValue = (typeof PERIOD_OPTIONS)[number]["value"];

export const DEFAULT_PERIOD: PeriodValue = "weekly";

export function formatPeriodLabel(period: PeriodValue): string {
  const match = PERIOD_OPTIONS.find((option) => option.value === period);
  return match?.label ?? period;
}
