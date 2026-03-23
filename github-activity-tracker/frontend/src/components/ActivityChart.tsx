import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const dottedGridPlugin = {
  id: "dottedGrid",
  afterDraw(chart: any) {
    const { ctx, chartArea, scales } = chart;
    const xScale = scales.x;
    const yScale = scales.y;

    ctx.save();
    ctx.strokeStyle = "rgba(0,0,0,0.12)";
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
    ctx.fillStyle = "rgba(0,0,0,0.07)";
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
    commits: number[];
    prs: number[];
    reviews: number[];
  };
  period: "daily" | "weekly" | "monthly";
  showTitle?: boolean;
}

const ActivityChart: React.FC<ActivityChartProps> = ({
  data,
  period,
  showTitle = true,
}) => {
  let labels = data?.labels ?? [];
  let commits = data?.commits ?? [];
  let pullRequests = data?.prs ?? [];
  let reviews = data?.reviews ?? [];

  /* -------------------------------
     WEEKLY AGGREGATION FOR MONTHLY
  -------------------------------- */

  if (period === "monthly" && labels.length > 0) {
    const weekLabels: string[] = [];
    const weekCommits: number[] = [];
    const weekPRs: number[] = [];
    const weekReviews: number[] = [];

    for (let i = 0; i < labels.length; i += 7) {
      const weekIndex = Math.floor(i / 7) + 1;

      weekLabels.push(`Week ${weekIndex}`);

      weekCommits.push(
        commits.slice(i, i + 7).reduce((a, b) => a + b, 0),
      );

      weekPRs.push(
        pullRequests.slice(i, i + 7).reduce((a, b) => a + b, 0),
      );

      weekReviews.push(
        reviews.slice(i, i + 7).reduce((a, b) => a + b, 0),
      );
    }

    labels = weekLabels;
    commits = weekCommits;
    pullRequests = weekPRs;
    reviews = weekReviews;
  }

  const COLOR_COMMITS = "#3B82F6";
  const COLOR_PULLS = "#10B981";
  const COLOR_REVIEWS = "#F59E0B";

  const chartData = {
    labels,
    datasets: [
      { label: "Commits", data: commits, backgroundColor: COLOR_COMMITS },
      {
        label: "Pull Requests",
        data: pullRequests,
        backgroundColor: COLOR_PULLS,
      },
      { label: "Reviews", data: reviews, backgroundColor: COLOR_REVIEWS },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom" },

      tooltip: {
        mode: "index",
        intersect: false,
        backgroundColor: "rgba(255,255,255,0.98)",
        borderColor: "rgba(0,0,0,0.2)",
        borderWidth: 1,
        cornerRadius: 8,
        padding: 14,

        titleColor: "#111",
        titleFont: { size: 18, weight: "600" },
        titleMarginBottom: 12,

        displayColors: false,
        bodyFont: { size: 16 },

        callbacks: {
          label: function (context: any) {
            const label = context.dataset.label;
            const value = context.raw;

            if (label === "Commits") return `Commits : ${value}`;
            if (label === "Pull Requests") return `Pull Requests : ${value}`;
            if (label === "Reviews") return `Reviews : ${value}`;

            return `${label} : ${value}`;
          },

          labelTextColor: function (context: any) {
            const label = context.dataset.label;
            if (label === "Commits") return COLOR_COMMITS;
            if (label === "Pull Requests") return COLOR_PULLS;
            if (label === "Reviews") return COLOR_REVIEWS;
            return "#111";
          },
        },
      },
    },

    hover: { mode: "index", intersect: false },

    scales: {
      x: { grid: { display: false } },
      y: {
        beginAtZero: true,
        ticks: { stepSize: 5 },
        grid: { display: false },
      },
    },
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm font-arimo">

      {showTitle && (
        <h2 className="text-gray-800 text-[18px] mb-4">
          Activity Overview –{" "}
          {period.charAt(0).toUpperCase() + period.slice(1)}
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