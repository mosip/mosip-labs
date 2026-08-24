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

  const chartData = {
    labels,
    datasets: [
      {
        label: "Pull Requests",
        data: data.map((d) => d.prs),
        borderColor: "#0EA5E9",
        backgroundColor: "#0EA5E9",
        tension: 0.4,
        pointRadius: 4,
        pointBorderWidth: 2,
      },
      {
        label: "Reviews",
        data: data.map((d) => d.reviews),
        borderColor: "#EA580C",
        backgroundColor: "#EA580C",
        tension: 0.4,
        pointRadius: 4,
        pointBorderWidth: 2,
      },
      {
        label: "Issues",
        data: data.map((d) => d.issues),
        borderColor: "#4F46E5",
        backgroundColor: "#4F46E5",
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
          color: "#334155",
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#64748b" },
      },
      y: {
        ticks: { color: "#64748b" },
        grid: {
          borderDash: [6, 6],
          color: "rgba(28,25,23,0.12)",
        },
      },
    },
  };

  return (
    <div className="panel-card rounded-2xl p-6 mb-8">
      <h2 className="text-2xl font-black mb-4 text-sky-800">
        Activity Trend
      </h2>
      <Line data={chartData} options={options} />
    </div>
  );
};

export default ActivityTrend;
