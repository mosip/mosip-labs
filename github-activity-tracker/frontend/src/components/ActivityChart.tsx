import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import type { ChartOptions } from "chart.js";
import { Bar } from "react-chartjs-2";
import { formatPeriodLabel, type PeriodValue } from "../lib/periods";
import { chartTheme } from "../lib/theme";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const dottedGridPlugin = {
  id: "dottedGrid",
  afterDraw(chart: any) {
    const { ctx, chartArea, scales } = chart;
    const xScale = scales.x;
    const yScale = scales.y;

    ctx.save();
    ctx.strokeStyle = chartTheme().grid;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    yScale.ticks.forEach((tick: any) => {
      const y = yScale.getPixelForValue(tick.value);
      ctx.beginPath();
      ctx.moveTo(chartArea.left, y);
      ctx.lineTo(chartArea.right, y);
      ctx.stroke();
    });

    xScale.ticks.forEach((tick: any) => {
      const x = xScale.getPixelForValue(tick.value);
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
    });

    ctx.restore();
  },
};

const columnHoverPlugin = {
  id: "columnHover",
  afterDraw(chart: any) {
    const { ctx, tooltip, chartArea, scales } = chart;
    if (!tooltip?._active?.length) return;

    const active = tooltip._active[0];
    const index = active.index;

    const xScale = scales.x;
    if (!xScale) return;

    const currentX = xScale.getPixelForTick(index);

    let categoryWidth;
    if (index === xScale.ticks.length - 1) {
      const prevX = xScale.getPixelForTick(index - 1);
      categoryWidth = currentX - prevX;
    } else {
      const nextX = xScale.getPixelForTick(index + 1);
      categoryWidth = nextX - currentX;
    }

    const highlightLeft = currentX - categoryWidth / 2;
    const highlightWidth = categoryWidth;

    ctx.save();
    ctx.fillStyle = chartTheme().hover;
    ctx.fillRect(
      highlightLeft,
      chartArea.top,
      highlightWidth,
      chartArea.bottom - chartArea.top,
    );
    ctx.restore();
  },
};

interface ActivityChartProps {
  data?: {
    labels: string[];
    prs: number[];
    reviews: number[];
    issues?: number[];
  };
  period: PeriodValue;
  showTitle?: boolean;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function formatMonthLabel(monthKey: string): string {
  const [year, month] = monthKey.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
}

function aggregateDailyIntoWeeks(
  labels: string[],
  pullRequests: number[],
  reviews: number[],
  issues: number[],
) {
  const weekLabels: string[] = [];
  const weekPRs: number[] = [];
  const weekReviews: number[] = [];
  const weekIssues: number[] = [];

  for (let i = 0; i < labels.length; i += 7) {
    const weekIndex = Math.floor(i / 7) + 1;
    weekLabels.push(`Week ${weekIndex}`);
    weekPRs.push(pullRequests.slice(i, i + 7).reduce((a, b) => a + b, 0));
    weekReviews.push(reviews.slice(i, i + 7).reduce((a, b) => a + b, 0));
    weekIssues.push(issues.slice(i, i + 7).reduce((a, b) => a + b, 0));
  }

  return { labels: weekLabels, pullRequests: weekPRs, reviews: weekReviews, issues: weekIssues };
}

function aggregateDailyIntoMonths(
  labels: string[],
  pullRequests: number[],
  reviews: number[],
  issues: number[],
) {
  const monthLabels: string[] = [];
  const monthPRs: number[] = [];
  const monthReviews: number[] = [];
  const monthIssues: number[] = [];

  let currentMonth = "";
  let prSum = 0;
  let reviewSum = 0;
  let issueSum = 0;

  const flush = (monthKey: string) => {
    monthLabels.push(formatMonthLabel(monthKey));
    monthPRs.push(prSum);
    monthReviews.push(reviewSum);
    monthIssues.push(issueSum);
    prSum = 0;
    reviewSum = 0;
    issueSum = 0;
  };

  for (let i = 0; i < labels.length; i++) {
    const monthKey = labels[i].slice(0, 7);
    if (currentMonth && monthKey !== currentMonth) {
      flush(currentMonth);
    }
    currentMonth = monthKey;
    prSum += pullRequests[i];
    reviewSum += reviews[i];
    issueSum += issues[i];
  }

  if (currentMonth) {
    flush(currentMonth);
  }

  return {
    labels: monthLabels,
    pullRequests: monthPRs,
    reviews: monthReviews,
    issues: monthIssues,
  };
}

const ActivityChart: React.FC<ActivityChartProps> = ({
  data,
  period,
  showTitle = true,
}) => {
  let labels = data?.labels ?? [];
  let pullRequests = data?.prs ?? [];
  let reviews = data?.reviews ?? [];
  let issues = data?.issues ?? [];

  /* -------------------------------
     WEEKLY AGGREGATION FOR MONTHLY
     (Skip if API already returned weekly buckets, e.g. "Week 1".)
  -------------------------------- */

  const isPreAggregatedWeekly =
    labels.length > 0 && labels.every((l) => /^Week\s+\d+$/i.test(l));

  const isPreAggregatedMonthly =
    labels.length > 0 &&
    labels.every((l) => !ISO_DATE.test(l));

  if (period === "monthly" && labels.length > 0 && !isPreAggregatedWeekly) {
    const aggregated = aggregateDailyIntoWeeks(labels, pullRequests, reviews, issues);
    labels = aggregated.labels;
    pullRequests = aggregated.pullRequests;
    reviews = aggregated.reviews;
    issues = aggregated.issues;
  }

  if (period === "yearly" && labels.length > 0 && !isPreAggregatedMonthly) {
    const aggregated = aggregateDailyIntoMonths(labels, pullRequests, reviews, issues);
    labels = aggregated.labels;
    pullRequests = aggregated.pullRequests;
    reviews = aggregated.reviews;
    issues = aggregated.issues;
  }

  const { prs: COLOR_PULLS, reviews: COLOR_REVIEWS, issues: COLOR_ISSUES, legend, tick, tooltipBg, tooltipBorder, title } = chartTheme();

  const chartData = {
    labels,
    datasets: [
      {
        label: "Pull Requests",
        data: pullRequests,
        backgroundColor: COLOR_PULLS,
      },
      { label: "Reviews", data: reviews, backgroundColor: COLOR_REVIEWS },
      { label: "Issues", data: issues, backgroundColor: COLOR_ISSUES },
    ],
  };

  const options: ChartOptions<"bar"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: { color: legend },
      },

      tooltip: {
        mode: "index" as const,
        intersect: false,
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        borderWidth: 1,
        cornerRadius: 8,
        padding: 14,

        titleColor: title,
        titleFont: { size: 18, weight: 600 },
        titleMarginBottom: 12,

        displayColors: false,
        bodyFont: { size: 16 },

        callbacks: {
          label: function (context: any) {
            const label = context.dataset.label;
            const value = context.raw;

            if (label === "Pull Requests") return `Pull Requests : ${value}`;
            if (label === "Reviews") return `Reviews : ${value}`;
            if (label === "Issues") return `Issues : ${value}`;

            return `${label} : ${value}`;
          },

          labelTextColor: function (context: any) {
            const label = context.dataset.label;
            if (label === "Pull Requests") return COLOR_PULLS;
            if (label === "Reviews") return COLOR_REVIEWS;
            if (label === "Issues") return COLOR_ISSUES;
            return title;
          },
        },
      },
    },

    hover: { mode: "index" as const, intersect: false },

    scales: {
      x: {
        grid: { display: false },
        ticks: { color: tick },
      },
      y: {
        beginAtZero: true,
        ticks: { stepSize: 5, color: tick },
        grid: { display: false },
      },
    },
  };

  return (
    <div className="bg-transparent p-0 rounded-xl font-arimo">

      {showTitle && (
        <h2 className="text-[22px] mb-4 font-black text-brand-dark">
          Activity Overview – {formatPeriodLabel(period)}
        </h2>
      )}

      <div className="w-full h-[380px]">
        <Bar
          data={chartData}
          options={options}
          plugins={[columnHoverPlugin, dottedGridPlugin]}
        />
      </div>
    </div>
  );
};

export default ActivityChart;