import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { chartTheme } from "../lib/theme";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

interface TrendPoint {
  date: string;
  prs: number;
  reviews: number;
  issues: number;
}

interface ActivityTrendProps {
  data: TrendPoint[];
}

const ActivityTrend: React.FC<ActivityTrendProps> = ({ data }) => {
  const labels = data.map((d) => d.date);
  const { prs, reviews, issues, legend, tick, grid } = chartTheme();

  const chartData = {
    labels,
    datasets: [
      {
        label: "Pull Requests",
        data: data.map((d) => d.prs),
        borderColor: prs,
        backgroundColor: prs,
        tension: 0.4,
        pointRadius: 4,
        pointBorderWidth: 2,
      },
      {
        label: "Reviews",
        data: data.map((d) => d.reviews),
        borderColor: reviews,
        backgroundColor: reviews,
        tension: 0.4,
        pointRadius: 4,
        pointBorderWidth: 2,
      },
      {
        label: "Issues",
        data: data.map((d) => d.issues),
        borderColor: issues,
        backgroundColor: issues,
        tension: 0.4,
        pointRadius: 4,
        pointBorderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "bottom" as const,
        labels: {
          usePointStyle: true,
          color: legend,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: tick },
      },
      y: {
        ticks: { color: tick },
        grid: {
          borderDash: [6, 6],
          color: grid,
        },
      },
    },
  };

  return (
    <div className="panel-card rounded-2xl p-6 mb-8">
      <h2 className="text-2xl font-black mb-4 text-brand-dark">
        Activity Trend
      </h2>
      <Line data={chartData} options={options} />
    </div>
  );
};

export default ActivityTrend;
