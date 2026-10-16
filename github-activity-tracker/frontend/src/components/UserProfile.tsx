import React, { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { StatsCard } from "./StatsCard";
import ActivityChart from "./ActivityChart";
import ActivityTrend from "./ActivityTrend";
import { fetchUserDetails } from "../lib/api";
import {
  formatPeriodLabel,
  PERIOD_OPTIONS,
  type PeriodValue,
} from "../lib/periods";

import PRIcon from "../assets/PRIcon.svg";
import CodeReviewIcon from "../assets/CodeReviewIcon.svg";
import IssueIcon from "../assets/IssueIcon.svg";
import DownloadIcon from "../assets/DownloadIcon.svg";
import ThemeSwitcher from "./ThemeSwitcher";
import CustomPeriodButton from "./CustomPeriodButton";
import { useTheme } from "../ThemeContext";

interface UserProfileProps {
  org: string;
  userName: string;
  onBack: () => void;
  period: PeriodValue;
  startDate: string;
  endDate: string;
  onPeriodChange: (p: PeriodValue) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
}

interface DailyActivityRow {
  date: string;
  prs: number;
  pr_files_changed: number;
  reviews: number;
  issues: number;
}

const UserProfile: React.FC<UserProfileProps> = ({
  org,
  userName,
  onBack,
  period,
  startDate,
  endDate,
  onPeriodChange,
  onStartDateChange,
  onEndDateChange,
}) => {
  const { theme } = useTheme();
  const [userData, setUserData] = useState<any>(null);

  useEffect(() => {
    if (period === "custom" && (!startDate || !endDate || startDate > endDate)) {
      return;
    }

    async function loadUser() {
      try {
        const data = await fetchUserDetails(
          org,
          userName,
          period,
          startDate,
          endDate,
        );
        setUserData(data);
      } catch (err) {
        console.error("Failed to load user details:", err);
      }
    }

    loadUser();
  }, [org, userName, period, startDate, endDate]);

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

  const detailed: DailyActivityRow[] = [...(userData?.daily_activity || [])].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  return (
    <div className="min-h-screen">
      <div className="app-header w-full text-white">
        <div className="app-stripe" />
        <div className="px-8 py-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-brand-muted hover:text-white mb-6 font-bold"
        >
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>

        <div className="flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-brand-softer text-brand-mid flex items-center justify-center text-3xl font-black shadow-lg">
              {(profile.name || "?").charAt(0).toUpperCase()}
            </div>

            <div>
              <h1 className="text-4xl font-black text-white">{profile.name}</h1>
              <a
                href={githubProfileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-muted hover:text-white hover:underline"
              >
                {githubProfileUrl}
              </a>
              <p className="text-brand-muted">
                {profile.team} • {profile.project}
              </p>
            </div>
          </div>
          <ThemeSwitcher />
        </div>

        <div className="flex justify-between items-center mt-8">
          <div className="flex items-center gap-4">
            {PERIOD_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => onPeriodChange(value)}
                className={`px-5 py-2 rounded-full font-black transition-all ${
                  period === value
                    ? "bg-brand-softer text-brand-dark shadow-lg"
                    : "bg-white/20 text-white hover:bg-white/30"
                }`}
              >
                {label}
              </button>
            ))}
            <CustomPeriodButton
              startDate={startDate}
              endDate={endDate}
              onPeriodChange={onPeriodChange}
              onStartDateChange={onStartDateChange}
              onEndDateChange={onEndDateChange}
              buttonClassName={`px-5 py-2 rounded-full font-black transition-all ${
                period === "custom"
                  ? "bg-brand-softer text-brand-dark shadow-lg"
                  : "bg-white/20 text-white hover:bg-white/30"
              }`}
            />
          </div>

          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 bg-csv hover:bg-csv-hover text-white px-5 py-2 rounded-full font-black">
              <img src={DownloadIcon} alt="download" className="w-4 h-4" />
              CSV
            </button>

            <button className="flex items-center gap-2 bg-brand hover:bg-brand-light text-white px-5 py-2 rounded-full font-black">
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
          <h2 className="text-2xl font-black mb-4 text-brand-dark">
            Activity Overview – {formatPeriodLabel(period)}
          </h2>

          <ActivityChart key={theme} data={chartData} period={period} showTitle={false} />
        </div>

        {/* Activity Trend */}
        <ActivityTrend
          key={theme}
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
          <h2 className="text-2xl font-black mb-4 text-brand-dark">
            Detailed Activity
          </h2>

          <table className="w-full">
            <thead>
              <tr className="text-left text-white bg-brand">
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
                <tr key={idx} className="border-b border-panel-border last:border-0 hover:bg-brand-softer">
                  <td className="py-3 px-3 text-gray-800">{row.date}</td>

                  <td className="font-black px-3 text-brand">
                    {row.prs}
                  </td>

                  <td className="font-medium text-gray-900 px-3">
                    {row.pr_files_changed ?? 0}
                  </td>

                  <td className="font-black px-3 text-review">
                    {row.reviews}
                  </td>

                  <td className="font-black px-3 text-issue">
                    {row.issues ?? 0}
                  </td>

                  <td className="font-black px-3 text-brand-dark">
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
