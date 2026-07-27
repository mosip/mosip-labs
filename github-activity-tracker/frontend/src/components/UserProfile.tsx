import React, { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { StatsCard } from "./StatsCard";
import ActivityChart from "./ActivityChart";
import ActivityTrend from "./ActivityTrend";
import { fetchUserDetails } from "../lib/api";
import {
  DEFAULT_PERIOD,
  formatPeriodLabel,
  PERIOD_OPTIONS,
  type PeriodValue,
} from "../lib/periods";

import PRIcon from "../assets/PRIcon.svg";
import CodeReviewIcon from "../assets/CodeReviewIcon.svg";
import IssueIcon from "../assets/IssueIcon.svg";
import DownloadIcon from "../assets/DownloadIcon.svg";

interface UserProfileProps {
  org: string;
  userName: string;
  onBack: () => void;
}

interface DailyActivityRow {
  date: string;
  prs: number;
  reviews: number;
  issues: number;
}

const UserProfile: React.FC<UserProfileProps> = ({ org, userName, onBack }) => {
  const [period, setPeriod] = useState<PeriodValue>(DEFAULT_PERIOD);

  const [userData, setUserData] = useState<any>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await fetchUserDetails(org, userName, period);
        setUserData(data);
      } catch (err) {
        console.error("Failed to load user details:", err);
      }
    }

    loadUser();
  }, [org, userName, period]);

  const githubUsername = userData?.login || userName;
  const githubProfileUrl = `https://github.com/${githubUsername}`;

  const profile = {
    name: githubUsername,
    team: userData?.team || "Frontend Team",
    project: userData?.project || "Project Alpha",
  };

  const prs = userData?.summary?.prs || 0;
  const reviews = userData?.summary?.reviews || 0;
  const issues = userData?.summary?.issues || 0;

  const changePRs = userData?.summary?.change?.prs;
  const changeReviews = userData?.summary?.change?.reviews;
  const changeIssues = userData?.summary?.change?.issues;

  const chartData = {
    labels: userData?.overview?.labels || [],
    prs: userData?.overview?.prs || [],
    reviews: userData?.overview?.reviews || [],
    issues: userData?.overview?.issues || [],
  };

  const detailed: DailyActivityRow[] = userData?.daily_activity || [];

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="w-full bg-white border-b shadow-sm px-8 py-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-blue-600 hover:underline mb-6"
        >
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>

        <div className="flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center text-4xl text-blue-600">
              👤
            </div>

            <div>
              <h1 className="text-4xl font-bold">{profile.name}</h1>
              <a
                href={githubProfileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {githubProfileUrl}
              </a>
              <p className="text-gray-500">
                {profile.team} • {profile.project}
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center mt-8">
          <div className="flex items-center gap-4">
            {PERIOD_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setPeriod(value)}
                className={`px-5 py-2 rounded-lg ${
                  period === value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg">
              <img src={DownloadIcon} alt="download" className="w-4 h-4" />
              CSV
            </button>

            <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg">
              <img src={DownloadIcon} alt="download" className="w-4 h-4" />
              JSON
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-10">
          <StatsCard
            title="Pull Requests"
            value={prs}
            change={changePRs}
            icon={PRIcon}
          />

          <StatsCard
            title="Code Reviews"
            value={reviews}
            change={changeReviews}
            icon={CodeReviewIcon}
          />

          <StatsCard
            title="Issues"
            value={issues}
            change={changeIssues}
            icon={IssueIcon}
          />
        </div>

        {/* Activity Chart */}
        <div className="bg-white border rounded-xl p-6 mb-8 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">
            Activity Overview – {formatPeriodLabel(period)}
          </h2>

          <ActivityChart data={chartData} period={period} showTitle={false} />
        </div>

        {/* Activity Trend */}
        <ActivityTrend
          data={
            userData?.trend?.labels?.map((label: string, i: number) => ({
              date: label,
              prs: userData.trend.prs[i],
              reviews: userData.trend.reviews[i],
              issues: userData.trend.issues?.[i] ?? 0,
            })) || []
          }
        />

        {/* Detailed Activity Table */}
        <div className="bg-white border rounded-xl p-6 shadow-sm mb-10">
          <h2 className="text-xl font-semibold mb-4">Detailed Activity</h2>

          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-600 border-b">
                <th className="pb-3">Date</th>
                <th className="pb-3">Pull Requests</th>
                <th className="pb-3">Reviews</th>
                <th className="pb-3">Issues</th>
                <th className="pb-3">Total</th>
              </tr>
            </thead>

            <tbody>
              {detailed.map((row, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="py-3">{row.date}</td>

                  <td className="font-medium" style={{ color: "#00A63E" }}>
                    {row.prs}
                  </td>

                  <td className="font-medium" style={{ color: "#F54900" }}>
                    {row.reviews}
                  </td>

                  <td className="font-medium" style={{ color: "#7C3AED" }}>
                    {row.issues ?? 0}
                  </td>

                  <td className="font-semibold">
                    {row.prs + row.reviews + (row.issues ?? 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;