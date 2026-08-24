const dayjs = require("dayjs");

const PRESET_PERIODS = ["daily", "weekly", "monthly", "yearly"];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_CUSTOM_DAYS = 365;

function getCustomDateRange(startDate, endDate) {
  if (
    typeof startDate !== "string" ||
    typeof endDate !== "string" ||
    !DATE_RE.test(startDate) ||
    !DATE_RE.test(endDate)
  ) {
    throw new Error("startDate and endDate (YYYY-MM-DD) are required for custom period");
  }

  const start = dayjs(startDate).startOf("day");
  const end = dayjs(endDate).endOf("day");

  if (!start.isValid() || !end.isValid()) {
    throw new Error("Invalid custom date range");
  }

  if (end.isBefore(start)) {
    throw new Error("endDate must be on or after startDate");
  }

  const days = end.startOf("day").diff(start, "day") + 1;
  if (days > MAX_CUSTOM_DAYS) {
    throw new Error("Custom date range cannot exceed 365 days");
  }

  const prevEnd = start.subtract(1, "millisecond");
  const prevStart = prevEnd.subtract(days - 1, "day").startOf("day");

  return {
    start: start.toDate(),
    end: end.toDate(),
    days,
    prevStart: prevStart.toDate(),
    prevEnd: prevEnd.toDate(),
  };
}

function resolvePeriodQuery(query, options = {}) {
  const period = query.period || "weekly";
  const startDate = query.startDate;
  const endDate = query.endDate;

  if (options.allowAll && period === "all") {
    return { period };
  }

  if (PRESET_PERIODS.includes(period)) {
    return { period };
  }

  if (period === "custom") {
    try {
      getCustomDateRange(startDate, endDate);
      return { period, startDate, endDate };
    } catch (err) {
      return { error: err.message };
    }
  }

  return { error: "Invalid period value" };
}

module.exports = {
  getCustomDateRange,
  resolvePeriodQuery,
};
