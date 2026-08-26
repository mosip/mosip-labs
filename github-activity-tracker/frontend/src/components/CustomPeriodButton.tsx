import React, { useEffect, useRef, useState } from "react";
import type { PeriodValue } from "../lib/periods";

interface CustomPeriodButtonProps {
  startDate: string;
  endDate: string;
  onPeriodChange: (p: PeriodValue) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
  buttonClassName: string;
}

const CustomPeriodButton: React.FC<CustomPeriodButtonProps> = ({
  startDate,
  endDate,
  onPeriodChange,
  onStartDateChange,
  onEndDateChange,
  buttonClassName,
}) => {
  const [showCustomPopup, setShowCustomPopup] = useState(false);
  const [draftStart, setDraftStart] = useState(startDate);
  const [draftEnd, setDraftEnd] = useState(endDate);
  const customPopupRef = useRef<HTMLDivElement>(null);

  const toYmd = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

  const openCustomPopup = () => {
    if (startDate && endDate) {
      setDraftStart(startDate);
      setDraftEnd(endDate);
    } else {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 6);
      setDraftStart(toYmd(start));
      setDraftEnd(toYmd(end));
    }
    setShowCustomPopup(true);
  };

  const applyCustomRange = () => {
    if (!draftStart || !draftEnd || draftStart > draftEnd) return;
    onStartDateChange(draftStart);
    onEndDateChange(draftEnd);
    onPeriodChange("custom");
    setShowCustomPopup(false);
  };

  useEffect(() => {
    if (!showCustomPopup) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        customPopupRef.current &&
        !customPopupRef.current.contains(event.target as Node)
      ) {
        setShowCustomPopup(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showCustomPopup]);

  return (
    <div className="relative" ref={customPopupRef}>
      <button type="button" className={buttonClassName} onClick={openCustomPopup}>
        Custom
      </button>
      {showCustomPopup && (
        <div className="absolute left-0 top-full mt-2 z-30 w-72 rounded-xl border border-panel-border bg-brand-softer p-4 shadow-lg">
          <p className="text-sm font-medium text-brand-ink mb-3">
            Custom date range
          </p>
          <label className="block text-xs text-brand-mid mb-1">From</label>
          <input
            type="date"
            value={draftStart}
            max={draftEnd || undefined}
            onChange={(e) => setDraftStart(e.target.value)}
            className="themed-date-input w-full mb-3 px-3 py-2 border border-panel-border rounded-lg bg-surface text-brand-ink text-sm"
          />
          <label className="block text-xs text-brand-mid mb-1">To</label>
          <input
            type="date"
            value={draftEnd}
            min={draftStart || undefined}
            onChange={(e) => setDraftEnd(e.target.value)}
            className="themed-date-input w-full mb-4 px-3 py-2 border border-panel-border rounded-lg bg-surface text-brand-ink text-sm"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded-lg text-sm text-brand-dark bg-surface border border-panel-border hover:bg-brand-soft"
              onClick={() => setShowCustomPopup(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded-full text-sm text-white bg-brand hover:bg-brand-hover disabled:opacity-50"
              disabled={!draftStart || !draftEnd || draftStart > draftEnd}
              onClick={applyCustomRange}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomPeriodButton;
