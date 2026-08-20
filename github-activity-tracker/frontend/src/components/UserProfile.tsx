import React, { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { StatsCard } from "./StatsCard";
import ActivityChart from "./ActivityChart";
import ActivityTrend from "./ActivityTrend";
import { fetchUserDetails } from "../lib/api";

import CommitIcon from "../assets/CommitIcon.svg";
import PRIcon from "../assets/PRIcon.svg";
import CodeReviewIcon from "../assets/CodeReviewIcon.svg";
import DownloadIcon from "../assets/DownloadIcon.svg";

interface UserProfileProps {
  userName: string;
  onBack: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ userName, onBack }) => {
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">(
    "weekly",
  );

  const [userData, setUserData] = useState<any>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await fetchUserDetails("mosip", userName, period);
        setUserData(data);
      } catch (err) {
        console.error("Failed to load user details:", err);
      }
    }

    loadUser();
  }, [userName, period]);

  const profile = {
    name: userData?.login || userName,
    email:
      userData?.email ||
      `${userName.toLowerCase().replace(" ", ".")}@company.com`,
    team: userData?.team || "Frontend Team",
    project: userData?.project || "Project Alpha",
  };

  const commits = userData?.summary?.commits || 0;
  const prs = userData?.summary?.prs || 0;
  const reviews = userData?.summary?.reviews || 0;

  const changeCommits = userData?.summary?.change?.commits;
  const changePRs = userData?.summary?.change?.prs;
  const changeReviews = userData?.summary?.change?.reviews;

  const chartData = {
    labels: userData?.overview?.labels || [],
    commits: userData?.overview?.commits || [],
    prs: userData?.overview?.prs || [],
    reviews: userData?.overview?.reviews || [],
  };

  const detailed = userData?.daily_activity || [];

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
              <p className="text-gray-600">{profile.email}</p>
              <p className="text-gray-500">
                {profile.team} • {profile.project}
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center mt-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setPeriod("daily")}
              className={`px-5 py-2 rounded-lg ${
                period === "daily"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              Daily
            </button>

            <button
              onClick={() => setPeriod("weekly")}
              className={`px-5 py-2 rounded-lg ${
                period === "weekly"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              Weekly
            </button>

            <button
              onClick={() => setPeriod("monthly")}
              className={`px-5 py-2 rounded-lg ${
                period === "monthly"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              Monthly
            </button>
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
            title="Commits"
            value={commits}
            change={changeCommits}
            icon={CommitIcon}
          />

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
        </div>

        {/* Activity Chart */}
        <div className="bg-white border rounded-xl p-6 mb-8 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">
            Activity Overview –{" "}
            {period.charAt(0).toUpperCase() + period.slice(1)}
          </h2>

          <ActivityChart data={chartData} period={period} showTitle={false} />
        </div>

        {/* Activity Trend */}
        <ActivityTrend
          data={
            userData?.trend?.labels?.map((label: string, i: number) => ({
              date: label,
              commits: userData.trend.commits[i],
              prs: userData.trend.prs[i],
              reviews: userData.trend.reviews[i],
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
                <th className="pb-3">Commits</th>
                <th className="pb-3">Pull Requests</th>
                <th className="pb-3">Reviews</th>
                <th className="pb-3">Total</th>
              </tr>
            </thead>

            <tbody>
              {detailed.map((row, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="py-3">{row.date}</td>

                  <td className="font-medium" style={{ color: "#155DFC" }}>
                    {row.commits}
                  </td>

                  <td className="font-medium" style={{ color: "#00A63E" }}>
                    {row.prs}
                  </td>

                  <td className="font-medium" style={{ color: "#F54900" }}>
                    {row.reviews}
                  </td>

                  <td className="font-semibold">
                    {row.commits + row.prs + row.reviews}
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