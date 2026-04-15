import { useState, useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";

import { StatsCard } from "./components/StatsCard";
import ActivityChart from "./components/ActivityChart";
import TopNav from "./components/TopNav";
import TeamMembers from "./components/TeamMembers";
import LeaderboardCard from "./components/LeaderboardCard";
import UserProfile from "./components/UserProfile";

import { useGitHubActivity } from "./lib/hooks";
import { useDashboardData, useLeaderboardData } from "./lib/usePageData";

/* SVG ICON IMPORTS */
import CommitIcon from "./assets/CommitIcon.svg";
import PRIcon from "./assets/PRIcon.svg";
import CodeReviewIcon from "./assets/CodeReviewIcon.svg";
import TotalActivityIcon from "./assets/TotalActivityIcon.svg";

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activePage, setActivePage] = useState<
    "dashboard" | "leaderboard" | "profile"
  >("dashboard");

  const periodFromUrl =
    (searchParams.get("period") as "daily" | "weekly" | "monthly" | null) ||
    "weekly";

  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">(
    periodFromUrl,
  );

  const isDashboard = location.pathname.startsWith("/dashboard");
  const isLeaderboard = location.pathname.startsWith("/leaderboard");

  const { summary, activityChartData } = useDashboardData(period, isDashboard);

  const { leaderboard } = useLeaderboardData(period, isLeaderboard);
  const { loading, error } = useGitHubActivity(
    "all",
    "all",
    "",
    "",
    false,
    "",
    [],
    [],
  );

  // Sync route -> activePage
  useEffect(() => {
    if (location.pathname.startsWith("/dashboard")) {
      setActivePage("dashboard");
    } else if (location.pathname.startsWith("/leaderboard")) {
      setActivePage("leaderboard");
    } else if (location.pathname.startsWith("/profile")) {
      setActivePage("profile");
    }
  }, [location.pathname]);

  // Sync period -> URL only for dashboard + leaderboard
  useEffect(() => {
    if (location.pathname.startsWith("/profile")) return;

    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("period", period);
      return params;
    });
  }, [period, setSearchParams, location.pathname]);

  const handleSelectUser = (name: string) => {
    setActivePage("profile");
    navigate(`/profile/${name}?period=${period}`);
  };

  const handlePageChange = (page: "dashboard" | "leaderboard" | "profile") => {
    setActivePage(page);

    if (page === "dashboard") navigate(`/dashboard?period=${period}`);
    if (page === "leaderboard") navigate(`/leaderboard?period=${period}`);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {!location.pathname.startsWith("/profile") && (
        <TopNav
          activePage={activePage}
          onChange={handlePageChange}
          title="GitHub Activity Tracker"
          period={period}
          onPeriodChange={setPeriod}
          team="all"
          onTeamChange={() => {}}
          project="all"
          onProjectChange={() => {}}
          onDownloadCSV={() => {}}
          onDownloadJSON={() => {}}
        />
      )}

      {location.pathname.startsWith("/profile") && username && (
        <UserProfile
          userName={username}
          onBack={() => {
            setActivePage("dashboard");
            navigate(`/dashboard?period=${period}`);
          }}
        />
      )}

      {location.pathname.startsWith("/dashboard") && (
        <main className="font-arimo max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {loading && <p>Loading...</p>}
          {error && <p className="text-red-500">{error}</p>}

          {!loading && !error && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
                <StatsCard
                  title="Total Commits"
                  value={summary?.total_commits ?? 0}
                  change={summary?.change?.commits}
                  icon={CommitIcon}
                />
                <StatsCard
                  title="Pull Requests"
                  value={summary?.total_prs ?? 0}
                  change={summary?.change?.prs}
                  icon={PRIcon}
                />
                <StatsCard
                  title="Reviews"
                  value={summary?.total_reviews ?? 0}
                  change={summary?.change?.reviews}
                  icon={CodeReviewIcon}
                />
                <StatsCard
                  title="Total Activity"
                  value={summary?.total_activity ?? 0}
                  change={summary?.change?.activity}
                  icon={TotalActivityIcon}
                />
              </div>

              <div className="bg-white border rounded-xl shadow-sm p-6 mb-8">
                <ActivityChart data={activityChartData} period={period} />
              </div>

              <TeamMembers
                team="all"
                project="all"
                period={period}
                onSelectUser={handleSelectUser}
              />
            </>
          )}
        </main>
      )}

      {location.pathname.startsWith("/leaderboard") && (
        <main className="font-arimo max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-arimo font-bold mb-6">Leaderboard</h1>
          <LeaderboardCard leaders={leaderboard} />
        </main>
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<AppContent />} />
        <Route path="/leaderboard" element={<AppContent />} />
        <Route path="/profile/:username" element={<AppContent />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
