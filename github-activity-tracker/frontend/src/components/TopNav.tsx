import React, { useEffect, useState } from "react";

import { PERIOD_OPTIONS, type PeriodValue } from "../lib/periods";
import { fetchUserRoles } from "../lib/api";
import type { Organization } from "../lib/organizations";
import DashboardIconWhite from "../assets/DashboardIconWhite.svg";
import DashboardIconBlack from "../assets/DashboardIconBlack.svg";
import LeaderboardIconWhite from "../assets/LeaderboardIconWhite.svg";
import LeaderboardIconBlack from "../assets/LeaderboardIconBlack.svg";
import DownloadIcon from "../assets/DownloadIcon.svg";

interface TopNavProps {
  activePage: "dashboard" | "leaderboard";
  onChange: (page: "dashboard" | "leaderboard") => void;

  title: string;

  period: PeriodValue;
  onPeriodChange: (p: PeriodValue) => void;

  organization: string;
  organizations: Organization[];
  onOrganizationChange: (value: string) => void;

  role: string;
  onRoleChange: (value: string) => void;

  onDownloadCSV: () => void;
  onDownloadJSON: () => void;
}

const TopNav: React.FC<TopNavProps> = ({
  activePage,
  onChange,
  title,
  period,
  onPeriodChange,
  organization,
  organizations,
  onOrganizationChange,
  role,
  onRoleChange,
  onDownloadCSV,
  onDownloadJSON,
}) => {
  const [userRoles, setUserRoles] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadRoles() {
      try {
        const roles = await fetchUserRoles();
        if (!cancelled) {
          setUserRoles(roles.map((role) => role.name));
        }
      } catch (error) {
        console.error("Failed to load user roles:", error);
      }
    }

    loadRoles();
    return () => {
      cancelled = true;
    };
  }, []);

  const tabStyle = (active: boolean) =>
    `px-4 py-2 rounded-lg font-medium transition-all ${
      active
        ? "bg-blue-600 font-arimo text-white"
        : "text-gray-600 font-arimo hover:text-black"
    }`;

  const periodBtn = (active: boolean) =>
    `px-4 py-2 rounded-lg font-arimo font-medium transition-all ${
      active
        ? "bg-blue-600 font-arimo text-white shadow"
        : "bg-gray-100 font-arimo text-gray-700 hover:bg-gray-200"
    }`;

  const filterSelectClass =
    "w-44 px-4 py-2 border rounded-lg bg-white";

  return (
    <div className="w-full bg-white border-b shadow-sm pb-6 font-arimo">
      <div className="max-w-7xl mx-auto px-6 py-4 flex font-arimo items-center gap-6">

        {/* DASHBOARD BUTTON */}
        <button
          onClick={() => onChange("dashboard")}
          className={tabStyle(activePage === "dashboard")}
          style={{ fontFamily: "Arimo, sans-serif" }}
        >
          <div className="flex items-center font-arimo gap-2">
            <img
              src={
                activePage === "dashboard"
                  ? DashboardIconWhite
                  : DashboardIconBlack
              }
              alt="dashboard"
              className="w-4 h-4"
            />
            Dashboard
          </div>
        </button>

        {/* LEADERBOARD BUTTON */}
        <button
          onClick={() => onChange("leaderboard")}
          className={tabStyle(activePage === "leaderboard")}
          style={{ fontFamily: "Arimo, sans-serif" }}
        >
          <div className="flex items-center font-arimo gap-2">
            <img
              src={
                activePage === "leaderboard"
                  ? LeaderboardIconWhite
                  : LeaderboardIconBlack
              }
              alt="leaderboard"
              className="w-4 h-4"
            />
            Leaderboard
          </div>
        </button>
      </div>

      <div className="border-b"></div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <h1
          className="text-3xl font-bold font-arimo text-gray-900"
          style={{ fontFamily: "Arimo, sans-serif" }}
        >
          {activePage === "dashboard"
            ? "GitHub Activity Tracker"
            : "Leaderboard"}
        </h1>
      </div>

      <div className="max-w-7xl mx-auto px-6 mt-4 flex flex-wrap items-end gap-10">

        {/* PERIOD + ORGANIZATION */}
        <div className="flex items-end gap-6">

          <div className="flex flex-col">
            <label className="text-gray-600 text-sm font-medium mb-2">
              Period
            </label>

            <div className="flex items-center gap-2">
              {PERIOD_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  className={periodBtn(period === value)}
                  onClick={() => onPeriodChange(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col">
            <label className="text-gray-600 text-sm font-medium mb-2">
              Organization
            </label>

            <select
              value={organization}
              onChange={(e) => onOrganizationChange(e.target.value)}
              className={filterSelectClass}
            >
              {organizations.map((org) => (
                <option key={org.id} value={org.slug}>
                  {org.name}
                </option>
              ))}
            </select>
          </div>

        </div>

        {/* ROLE */}
        <div className="flex flex-col">
          <label className="text-gray-600 text-sm font-medium mb-2">
            Role
          </label>

          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            className={filterSelectClass}
          >
            <option value="all">All Roles</option>
            {userRoles.map((userRole) => (
              <option key={userRole} value={userRole}>
                {userRole}
              </option>
            ))}
          </select>
        </div>

        {/* CSV */}
        <div className="flex flex-col">
          <label className="text-gray-600 text-sm font-medium mb-2">
            &nbsp;
          </label>

          <button
            onClick={onDownloadCSV}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
          >
            <img src={DownloadIcon} alt="download" className="w-4 h-4" />
            CSV
          </button>
        </div>

        {/* JSON */}
        <div className="flex flex-col">
          <label className="text-gray-600 text-sm font-medium mb-2">
            &nbsp;
          </label>

          <button
            onClick={onDownloadJSON}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            <img src={DownloadIcon} alt="download" className="w-4 h-4" />
            JSON
          </button>
        </div>

      </div>
    </div>
  );
};

export default TopNav;