import { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useSearchParams,
  matchPath,
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

type Period = "daily" | "weekly" | "monthly";

function parsePeriod(value: string | null): Period {
  return value === "daily" || value === "weekly" || value === "monthly"
    ? value
    : "weekly";
}

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const isDashboard = location.pathname.startsWith("/dashboard");
  const isLeaderboard = location.pathname.startsWith("/leaderboard");
  const isProfile = location.pathname.startsWith("/profile");
  const username = matchPath(
    "/profile/:username",
    location.pathname,
  )?.params.username;
  const activePage: "dashboard" | "leaderboard" | "profile" = isDashboard
    ? "dashboard"
    : isLeaderboard
      ? "leaderboard"
      : "profile";
  const periodParam = searchParams.get("period");
  const period = parsePeriod(periodParam);

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

  useEffect(() => {
    if (periodParam === period) return;

    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("period", period);
      return params;
    }, { replace: true });
  }, [period, periodParam, setSearchParams]);

  const handlePeriodChange = (nextPeriod: Period) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("period", nextPeriod);
      return params;
    });
  };

  const handleSelectUser = (name: string) => {
    navigate(`/profile/${name}?period=${period}`);
  };

  const handlePageChange = (page: "dashboard" | "leaderboard" | "profile") => {
    if (page === "dashboard") navigate(`/dashboard?period=${period}`);
    if (page === "leaderboard") navigate(`/leaderboard?period=${period}`);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {!isProfile && (
        <TopNav
          activePage={activePage}
          onChange={handlePageChange}
          title="GitHub Activity Tracker"
          period={period}
          onPeriodChange={handlePeriodChange}
          team="all"
          onTeamChange={() => {}}
          project="all"
          onProjectChange={() => {}}
          onDownloadCSV={() => {}}
          onDownloadJSON={() => {}}
        />
      )}

      {isProfile && username && (
        <UserProfile
          userName={username}
          onBack={() => navigate(`/dashboard?period=${period}`)}
        />
      )}

      {isDashboard && (
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

      {isLeaderboard && (
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
        <Route element={<AppContent />}>
          <Route path="/dashboard" />
          <Route path="/leaderboard" />
          <Route path="/profile/:username" />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
