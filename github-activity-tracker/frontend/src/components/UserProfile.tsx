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
  pr_files_changed: number;
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
    <div className="min-h-screen">
      <div className="app-header w-full text-white">
        <div className="h-1.5 bg-gradient-to-r from-sky-200 via-sky-300 to-cyan-100" />
        <div className="px-8 py-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sky-50 hover:text-white mb-6 font-bold"
        >
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>

        <div className="flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-[#f3f9ff] text-sky-700 flex items-center justify-center text-3xl font-black shadow-lg">
              {(profile.name || "?").charAt(0).toUpperCase()}
            </div>

            <div>
              <h1 className="text-4xl font-black text-white">{profile.name}</h1>
              <a
                href={githubProfileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-200 hover:text-white hover:underline"
              >
                {githubProfileUrl}
              </a>
              <p className="text-sky-100">
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
                className={`px-5 py-2 rounded-full font-black transition-all ${
                  period === value
                    ? "bg-[#f3f9ff] text-sky-800 shadow-lg"
                    : "bg-white/20 text-white hover:bg-white/30"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 bg-orange-400 hover:bg-orange-500 text-white px-5 py-2 rounded-full font-black">
              <img src={DownloadIcon} alt="download" className="w-4 h-4" />
              CSV
            </button>

            <button className="flex items-center gap-2 bg-sky-500 hover:bg-sky-400 text-white px-5 py-2 rounded-full font-black">
              <img src={DownloadIcon} alt="download" className="w-4 h-4" />
              JSON
            </button>
          </div>
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
            accent="emerald"
          />

          <StatsCard
            title="Code Reviews"
            value={reviews}
            change={changeReviews}
            icon={CodeReviewIcon}
            accent="amber"
          />

          <StatsCard
            title="Issues"
            value={issues}
            change={changeIssues}
            icon={IssueIcon}
            accent="violet"
          />
        </div>

        {/* Activity Chart */}
        <div className="panel-card rounded-2xl p-6 mb-8">
          <h2 className="text-2xl font-black mb-4 text-sky-800">
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
        <div className="panel-card rounded-2xl p-6 mb-10">
          <h2 className="text-2xl font-black mb-4 text-sky-800">
            Detailed Activity
          </h2>

          <table className="w-full">
            <thead>
              <tr className="text-left text-white bg-sky-500">
                <th className="p-3">Date</th>
                <th className="p-3">Pull Requests</th>
                <th className="p-3">File Changes</th>
                <th className="p-3">Reviews</th>
                <th className="p-3">Issues</th>
                <th className="p-3">Total</th>
              </tr>
            </thead>

            <tbody>
              {detailed.map((row, idx) => (
                <tr key={idx} className="border-b border-[#e3eef6] last:border-0 hover:bg-[#f3f9ff]">
                  <td className="py-3 px-3 text-gray-800">{row.date}</td>

                  <td className="font-black px-3 text-sky-600">
                    {row.prs}
                  </td>

                  <td className="font-medium text-gray-900 px-3">
                    {row.pr_files_changed ?? 0}
                  </td>

                  <td className="font-black px-3 text-orange-600">
                    {row.reviews}
                  </td>

                  <td className="font-black px-3 text-indigo-600">
                    {row.issues ?? 0}
                  </td>

                  <td className="font-black px-3 text-sky-800">
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