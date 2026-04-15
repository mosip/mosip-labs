import { useEffect, useState } from "react";
import {
  fetchUsers,
  fetchOrgSummary,
  fetchOrgActivity,
  fetchLeaderboard,
} from "./api";

export function useDashboardData(
  period: "daily" | "weekly" | "monthly",
  enabled: boolean
) {
  const [users, setUsers] = useState<string[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [activityChartData, setActivityChartData] = useState<any | null>(null);

  useEffect(() => {
    if (!enabled) return;

    async function loadDashboard() {
      try {
        const [usersData, summaryData, activityData] = await Promise.all([
          fetchUsers(),
          fetchOrgSummary("mosip", period),
          fetchOrgActivity("mosip", period),
        ]);

        setUsers(usersData);
        setSummary(summaryData);
        setActivityChartData(activityData);
      } catch (err) {
        console.error("Dashboard API error:", err);
      }
    }

    loadDashboard();
  }, [period, enabled]);

  return { users, summary, activityChartData };
}

export function useLeaderboardData(
  period: "daily" | "weekly" | "monthly",
  enabled: boolean
) {
  const [leaderboard, setLeaderboard] = useState<any[]>([]);

  useEffect(() => {
    if (!enabled) return;

    async function loadLeaderboard() {
      try {
        const data = await fetchLeaderboard("mosip", period, 10);

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
        console.error("Leaderboard API error:", err);
      }
    }

    loadLeaderboard();
  }, [period, enabled]);

  return { leaderboard };
}