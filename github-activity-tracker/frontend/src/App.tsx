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
import IssueIcon from "./assets/IssueIcon.svg";
import TotalActivityIcon from "./assets/TotalActivityIcon.svg";
import { useTheme } from "./ThemeContext";

function App() {
  const { theme } = useTheme();
  const [activePage, setActivePage] = useState<
    "dashboard" | "leaderboard" | "profile"
  >("dashboard");

  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [period, setPeriod] = useState<PeriodValue>(DEFAULT_PERIOD);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [role, setRole] = useState("all");

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
    if (period === "custom" && (!startDate || !endDate || startDate > endDate)) return;

    let cancelled = false;

    async function loadDashboard() {
      setDashboardLoading(true);
      setDashboardError(null);

      try {
        const [summaryData, activityData] = await Promise.all([
          fetchOrgSummary(selectedOrg, period, role, startDate, endDate),
          fetchOrgActivity(selectedOrg, period, role, startDate, endDate),
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
  }, [selectedOrg, period, role, startDate, endDate]);

  useEffect(() => {
    if (!selectedOrg) return;
    if (period === "custom" && (!startDate || !endDate || startDate > endDate)) return;

    async function loadLeaderboard() {
      try {
        const data = await fetchLeaderboard(selectedOrg, period, role, 10, startDate, endDate);

        const list = Array.isArray(data) ? data : data?.leaderboard || [];

        const ranked = list.map((u: any) => ({
          name: u.name || u.login,
          login: u.login,
          team: "—",
          project: "—",
          prs: u.prs,
          reviews: u.reviews,
          issues: u.issues ?? 0,
          total: u.score,
        }));

        setLeaderboard(ranked);
      } catch (err) {
        console.error("Error loading leaderboard:", err);
      }
    }

    loadLeaderboard();
  }, [selectedOrg, period, role, startDate, endDate]);

  const handleOrganizationChange = (org: string) => {
    setSelectedOrg(org);
    setRole("all");
  };

  const handlePeriodChange = (nextPeriod: PeriodValue) => {
    setPeriod(nextPeriod);
  };

  const handleSelectUser = (name: string) => {
    setSelectedUser(name);
    setActivePage("profile");
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="orb h-72 w-72 bg-orb-1 top-24 -left-16" style={{ animation: "floaty 8s ease-in-out infinite" }} />
      <div className="orb h-80 w-80 bg-orb-2 bottom-10 -right-10" style={{ animation: "floaty 10s ease-in-out infinite" }} />
      <div className="orb h-56 w-56 bg-orb-3 top-1/2 left-1/3" style={{ animation: "floaty 12s ease-in-out infinite" }} />

      <div className="relative z-10">
      {activePage !== "profile" && (
        <TopNav
          activePage={activePage}
          onChange={setActivePage}
          title="GitHub Activity Tracker"
          organization={selectedOrg}
          organizations={organizations}
          onOrganizationChange={handleOrganizationChange}
          period={period}
          onPeriodChange={handlePeriodChange}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          role={role}
          onRoleChange={setRole}
          onDownloadCSV={() => {}}
          onDownloadJSON={() => {}}
        />
      )}

      {activePage === "profile" && selectedUser && (
        <UserProfile
          org={selectedOrg}
          userName={selectedUser}
          onBack={() => setActivePage("dashboard")}
          period={period}
          startDate={startDate}
          endDate={endDate}
          onPeriodChange={handlePeriodChange}
        />
      )}

      {activePage === "dashboard" && (
        <main className="font-arimo max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {dashboardLoading && (
            <p className="text-on-page font-black tracking-wide">Loading...</p>
          )}
          {dashboardError && (
            <p className="text-rose-500 font-medium">{dashboardError}</p>
          )}

          {!dashboardLoading && !dashboardError && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
                <StatsCard
                  title="Total Activity"
                  value={summary?.total_activity ?? 0}
                  change={summary?.change?.activity}
                  icon={TotalActivityIcon}
                  accent="sky"
                  featured
                  className="md:col-span-2 xl:row-span-2"
                />

                <StatsCard
                  title="Pull Requests"
                  value={summary?.total_prs ?? 0}
                  change={summary?.change?.prs}
                  icon={PRIcon}
                  accent="emerald"
                />

                <StatsCard
                  title="Reviews"
                  value={summary?.total_reviews ?? 0}
                  change={summary?.change?.reviews}
                  icon={CodeReviewIcon}
                  accent="amber"
                />

                <StatsCard
                  title="Issues"
                  value={summary?.total_issues ?? 0}
                  change={summary?.change?.issues}
                  icon={IssueIcon}
                  accent="violet"
                  className="md:col-span-2 xl:col-span-2"
                />
              </div>

              <div className="panel-card rounded-2xl p-6 mb-8">
                <ActivityChart key={theme} data={activityChartData} period={period} />
              </div>

              <TeamMembers
                org={selectedOrg}
                role={role}
                period={period}
                startDate={startDate}
                endDate={endDate}
                onSelectUser={handleSelectUser}
              />
            </>
          )}
        </main>
      )}

      {activePage === "leaderboard" && (
        <main className="font-arimo max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-4xl font-arimo font-black mb-6 text-on-page">
            Leaderboard
          </h1>

          <LeaderboardCard leaders={leaderboard} />
        </main>
      )}
      </div>
    </div>
  );
}

export default App;
