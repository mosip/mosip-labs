import { useState, useEffect } from "react";

import { StatsCard } from "./components/StatsCard";
import ActivityChart from "./components/ActivityChart";
import TopNav from "./components/TopNav";
import TeamMembers from "./components/TeamMembers";
import LeaderboardCard from "./components/LeaderboardCard";
import UserProfile from "./components/UserProfile";

import { DEFAULT_PERIOD, type PeriodValue } from "./lib/periods";
import {
  fetchOrgSummary,
  fetchOrgActivity,
  fetchLeaderboard,
  fetchOrganizations,
} from "./lib/api";
import type { Organization } from "./lib/organizations";

/* SVG ICON IMPORTS */
import PRIcon from "./assets/PRIcon.svg";
import CodeReviewIcon from "./assets/CodeReviewIcon.svg";
import TotalActivityIcon from "./assets/TotalActivityIcon.svg";

function App() {
  const [activePage, setActivePage] = useState<
    "dashboard" | "leaderboard" | "profile"
  >("dashboard");

  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [period, setPeriod] = useState<PeriodValue>(DEFAULT_PERIOD);
  const [role, setRole] = useState("all");
  const [project, setProject] = useState("all");

  const [summary, setSummary] = useState<any | null>(null);
  const [activityChartData, setActivityChartData] = useState<any | null>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadOrganizations() {
      try {
        const orgs = await fetchOrganizations();
        if (cancelled) return;

        setOrganizations(orgs);
        if (orgs.length === 0) {
          setDashboardError("No organizations are available");
          setDashboardLoading(false);
          return;
        }

        setSelectedOrg((current) => current || orgs[0].slug);
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading organizations:", err);
        setDashboardError("Failed to load organizations");
        setDashboardLoading(false);
      }
    }

    loadOrganizations();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedOrg) return;

    let cancelled = false;

    async function loadDashboard() {
      setDashboardLoading(true);
      setDashboardError(null);

      try {
        const [summaryData, activityData] = await Promise.all([
          fetchOrgSummary(selectedOrg, period, role),
          fetchOrgActivity(selectedOrg, period, role),
        ]);

        if (cancelled) return;

        setSummary(summaryData);
        setActivityChartData(activityData);
      } catch (err: any) {
        if (cancelled) return;
        console.error("Error loading dashboard:", err);
        setDashboardError(err.message || "Failed to load dashboard data");
      } finally {
        if (!cancelled) setDashboardLoading(false);
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [selectedOrg, period, role]);

  useEffect(() => {
    if (!selectedOrg) return;

    async function loadLeaderboard() {
      try {
        const data = await fetchLeaderboard(selectedOrg, period, role, 10);

        const list = Array.isArray(data) ? data : data?.leaderboard || [];

        const ranked = list.map((u: any) => ({
          name: u.name || u.login,
          login: u.login,
          team: "—",
          project: "—",
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
  }, [selectedOrg, period, role]);

  const handleOrganizationChange = (org: string) => {
    setSelectedOrg(org);
    setProject("all");
    setRole("all");
  };

  const handleSelectUser = (name: string) => {
    setSelectedUser(name);
    setActivePage("profile");
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {activePage !== "profile" && (
        <TopNav
          activePage={activePage}
          onChange={setActivePage}
          title="GitHub Activity Tracker"
          organization={selectedOrg}
          organizations={organizations}
          onOrganizationChange={handleOrganizationChange}
          period={period}
          onPeriodChange={setPeriod}
          role={role}
          onRoleChange={setRole}
          project={project}
          onProjectChange={setProject}
          onDownloadCSV={() => {}}
          onDownloadJSON={() => {}}
        />
      )}

      {activePage === "profile" && selectedUser && (
        <UserProfile
          org={selectedOrg}
          userName={selectedUser}
          onBack={() => setActivePage("dashboard")}
        />
      )}

      {activePage === "dashboard" && (
        <main className="font-arimo max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {dashboardLoading && <p>Loading...</p>}
          {dashboardError && <p className="text-red-500">{dashboardError}</p>}

          {!dashboardLoading && !dashboardError && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
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
                org={selectedOrg}
                role={role}
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
