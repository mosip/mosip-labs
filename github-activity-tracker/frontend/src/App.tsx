import { useState, useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
} from "react-router-dom";

import { StatsCard } from "./components/StatsCard";
import ActivityChart from "./components/ActivityChart";
import TopNav from "./components/TopNav";
import TeamMembers from "./components/TeamMembers";
import LeaderboardCard from "./components/LeaderboardCard";
import UserProfile from "./components/UserProfile";

import { useGitHubActivity } from "./lib/hooks";
import {
  fetchUsers,
  fetchOrgSummary,
  fetchOrgActivity,
  fetchLeaderboard,
} from "./lib/api";

/* SVG ICON IMPORTS */
import CommitIcon from "./assets/CommitIcon.svg";
import PRIcon from "./assets/PRIcon.svg";
import CodeReviewIcon from "./assets/CodeReviewIcon.svg";
import TotalActivityIcon from "./assets/TotalActivityIcon.svg";

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username } = useParams();

  const [activePage, setActivePage] = useState<
    "dashboard" | "leaderboard" | "profile"
  >("dashboard");

  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">(
    "weekly"
  );

  const [users, setUsers] = useState<string[]>([]);
  const [summary, setSummary] = useState<any | null>(null);

  const [activityChartData, setActivityChartData] = useState<any | null>(null);

  const [leaderboard, setLeaderboard] = useState<any[]>([]);

  const { activities, loading, error } = useGitHubActivity(
    "all",
    "all",
    "",
    "",
    false,
    "",
    [],
    []
  );

  // Sync route -> activePage
  useEffect(() => {
    if (location.pathname.startsWith("/dashboard")) {
      setActivePage("dashboard");
    } else if (location.pathname.startsWith("/leaderboard")) {
      setActivePage("leaderboard");
    } else if (location.pathname.startsWith("/profile")) {
      setActivePage("profile");
      if (username) setSelectedUser(username);
    }
  }, [location.pathname, username]);

  useEffect(() => {
    async function loadUsers() {
      try {
        const list = await fetchUsers();
        setUsers(list);
      } catch (err) {
        console.error("Error fetching users:", err);
      }
    }
    loadUsers();
  }, []);

  useEffect(() => {
    async function loadSummary() {
      try {
        const data = await fetchOrgSummary("mosip", period);
        setSummary(data);
        console.log("ORG SUMMARY:", data);
      } catch (err) {
        console.error("Error fetching org summary:", err);
      }
    }

    loadSummary();
  }, [period]);

  useEffect(() => {
    async function loadActivity() {
      try {
        const data = await fetchOrgActivity("mosip", period);
        setActivityChartData(data);
        console.log("ORG ACTIVITY:", data);
      } catch (err) {
        console.error("Error fetching org activity:", err);
      }
    }

    loadActivity();
  }, [period]);

  useEffect(() => {
    async function loadLeaderboard() {
      try {
        const data = await fetchLeaderboard("mosip", period, 10);

        console.log("LEADERBOARD RAW:", data);

        const list = Array.isArray(data) ? data : data?.leaderboard || [];

        const ranked = list.map((u: any) => ({
          name: u.login,
          team: "—",
          project: "—",
          commits: u.commits,
          prs: u.prs,
          reviews: u.reviews,
          total: u.score,
        }));

        setLeaderboard(ranked);
      } catch (err) {
        console.error("Error loading leaderboard:", err);
      }
    }

    loadLeaderboard();
  }, [period]);

  const handleSelectUser = (name: string) => {
    setSelectedUser(name);
    setActivePage("profile");
    navigate(`/profile/${name}`);
  };

  const handlePageChange = (
    page: "dashboard" | "leaderboard" | "profile"
  ) => {
    setActivePage(page);

    if (page === "dashboard") navigate("/dashboard");
    if (page === "leaderboard") navigate("/leaderboard");
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {activePage !== "profile" && (
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

      {activePage === "profile" && selectedUser && (
        <UserProfile
          userName={selectedUser}
          onBack={() => {
            setActivePage("dashboard");
            navigate("/dashboard");
          }}
        />
      )}

      {activePage === "dashboard" && (
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

      {activePage === "leaderboard" && (
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