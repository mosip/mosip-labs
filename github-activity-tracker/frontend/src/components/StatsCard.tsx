import React from "react";
import { ArrowDown, ArrowUp } from "lucide-react";

type Accent = "emerald" | "amber" | "violet" | "sky";

interface StatsCardProps {
  title: string;
  value: number;
  change?: number;
  onClick?: () => void;
  icon?: string;
  showIcon?: boolean;
  accent?: Accent;
  featured?: boolean;
  className?: string;
}

const accentStyles: Record<
  Accent,
  { card: string; title: string; value: string; blob: string }
> = {
  emerald: {
    card: "bg-[#e8f4fb]",
    title: "text-sky-700",
    value: "text-sky-900",
    blob: "bg-sky-300/30",
  },
  amber: {
    card: "bg-[#fff3e8]",
    title: "text-orange-700",
    value: "text-orange-900",
    blob: "bg-orange-300/30",
  },
  violet: {
    card: "bg-[#eeedff]",
    title: "text-indigo-700",
    value: "text-indigo-900",
    blob: "bg-indigo-300/25",
  },
  sky: {
    card: "bg-[#def1fb]",
    title: "text-sky-700",
    value: "text-sky-900",
    blob: "bg-sky-300/35",
  },
};

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  change,
  onClick,
  icon,
  showIcon = false,
  accent = "sky",
  featured = false,
  className = "",
}) => {
  const isNegative = change !== undefined && change < 0;
  const isPositive = change !== undefined && change > 0;
  const styles = accentStyles[accent];

  return (
    <div
      onClick={onClick}
      className={`relative overflow-hidden rounded-[28px] cursor-pointer shadow-lg hover:-translate-y-1 hover:rotate-1 transition-transform ${styles.card} ${
        featured ? "p-8 min-h-[260px] flex flex-col justify-between" : "p-6"
      } ${className}`}
      style={{ fontFamily: "Arimo, sans-serif" }}
    >
      <div className={`absolute -right-10 -top-12 h-36 w-36 rounded-full ${styles.blob}`} />
      <div className={`absolute -right-4 bottom-0 h-24 w-24 rounded-full ${styles.blob}`} />

      <div className="relative flex items-center justify-between mb-4">
        <p className={`text-sm font-black tracking-[0.2em] uppercase ${styles.title}`}>
          {title}
        </p>

        {icon && (
          <div className="w-11 h-11 rounded-2xl bg-white/70 flex items-center justify-center">
            <img src={icon} alt="icon" className="w-5 h-5" />
          </div>
        )}
        {showIcon && !icon && (
          <div className="w-11 h-11 rounded-2xl bg-white/70" />
        )}
      </div>

      <p
        className={`relative leading-none font-black ${styles.value} ${
          featured ? "text-7xl" : "text-5xl"
        }`}
      >
        {value}
      </p>

      {change !== undefined && (
        <div className="relative flex items-center gap-1 mt-4">
          {isNegative && <ArrowDown size={16} className="text-red-600" />}
          {isPositive && <ArrowUp size={16} className="text-sky-700" />}
          <span
            className={`text-sm font-semibold ${
              isNegative
                ? "text-red-600"
                : isPositive
                ? "text-sky-700"
                : "text-stone-500"
            }`}
          >
            {Math.abs(change)}% vs previous period
          </span>
        </div>
      )}
    </div>
  );
};
