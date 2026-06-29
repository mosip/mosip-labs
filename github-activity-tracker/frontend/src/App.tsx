import { useState, useEffect } from "react";

import { StatsCard } from "./components/StatsCard";
import ActivityChart from "./components/ActivityChart";
import TopNav from "./components/TopNav";
import TeamMembers from "./components/TeamMembers";
import LeaderboardCard from "./components/LeaderboardCard";
import UserProfile from "./components/UserProfile";

import { useGitHubActivity } from "./lib/hooks";
import {
  fetchProjects,
  fetchOrgSummary,
  fetchOrgActivity,
  fetchLeaderboard,
  downloadExport,
  type Project,
} from "./lib/api";

import CommitIcon from "./assets/CommitIcon.svg";
import PRIcon from "./assets/PRIcon.svg";
import CodeReviewIcon from "./assets/CodeReviewIcon.svg";
import TotalActivityIcon from "./assets/TotalActivityIcon.svg";

function App() {
  const [activePage, setActivePage] = useState<
    "dashboard" | "leaderboard" | "profile"
  >("dashboard");

  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [project, setProject] = useState("all");
  const [projects, setProjects] = useState<Project[]>([]);

  const [summary, setSummary] = useState<any | null>(null);
  const [activityChartData, setActivityChartData] = useState<any | null>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);

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
    async function loadProjects() {
      try {
        const list = await fetchProjects();
        setProjects(list);
      } catch (err) {
        console.error("Error fetching projects:", err);
      }
    }
    loadProjects();
  }, []);

  useEffect(() => {
    async function loadSummary() {
      try {
        const data = await fetchOrgSummary(period, project);
        setSummary(data);
      } catch (err) {
        console.error("Error fetching org summary:", err);
      }
    }

    loadSummary();
  }, [period, project]);

  useEffect(() => {
    async function loadActivity() {
      try {
        const data = await fetchOrgActivity(period, project);
        setActivityChartData(data);
      } catch (err) {
        console.error("Error fetching org activity:", err);
      }
    }

    loadActivity();
  }, [period, project]);

  useEffect(() => {
    async function loadLeaderboard() {
      try {
        const data = await fetchLeaderboard(project, period, 10);
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
  }, [period, project]);

  const handleSelectUser = (name: string) => {
    setSelectedUser(name);
    setActivePage("profile");
  };

  const handleDownloadCSV = async () => {
    try {
      await downloadExport(project, period, "csv");
    } catch (err) {
      console.error("CSV export failed:", err);
    }
  };

  const handleDownloadJSON = async () => {
    try {
      await downloadExport(project, period, "json");
    } catch (err) {
      console.error("JSON export failed:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {activePage !== "profile" && (
        <TopNav
          activePage={activePage}
          onChange={setActivePage}
          title="GitHub Activity Tracker"
          period={period}
          onPeriodChange={setPeriod}
          team="all"
          onTeamChange={() => {}}
          project={project}
          onProjectChange={setProject}
          projects={projects}
          onDownloadCSV={handleDownloadCSV}
          onDownloadJSON={handleDownloadJSON}
        />
      )}

      {activePage === "profile" && selectedUser && (
        <UserProfile
          userName={selectedUser}
          project={project}
          onBack={() => setActivePage("dashboard")}
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
                project={project}
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

export default App;
