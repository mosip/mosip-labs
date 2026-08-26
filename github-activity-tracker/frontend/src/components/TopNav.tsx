import React, { useEffect, useState } from "react";

import { PERIOD_OPTIONS, type PeriodValue } from "../lib/periods";
import { fetchUserRoles } from "../lib/api";
import type { Organization } from "../lib/organizations";
import DashboardIconWhite from "../assets/DashboardIconWhite.svg";
import DashboardIconBlack from "../assets/DashboardIconBlack.svg";
import LeaderboardIconWhite from "../assets/LeaderboardIconWhite.svg";
import LeaderboardIconBlack from "../assets/LeaderboardIconBlack.svg";
import DownloadIcon from "../assets/DownloadIcon.svg";
import ThemeSwitcher from "./ThemeSwitcher";
import CustomPeriodButton from "./CustomPeriodButton";

interface TopNavProps {
  activePage: "dashboard" | "leaderboard";
  onChange: (page: "dashboard" | "leaderboard") => void;

  title: string;

  period: PeriodValue;
  onPeriodChange: (p: PeriodValue) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;

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
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
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
    `px-4 py-2 rounded-full font-black transition-all ${
      active
        ? "bg-brand-softer font-arimo text-brand-dark shadow-lg"
        : "text-white font-arimo hover:bg-white/20"
    }`;

  const periodBtn = (active: boolean) =>
    `px-4 py-2 rounded-full font-arimo font-bold transition-all ${
      active
        ? "bg-brand-softer font-arimo text-brand-dark shadow-lg"
        : "bg-white/20 font-arimo text-white hover:bg-white/30"
    }`;

  const filterSelectClass =
    "w-44 px-4 py-2 border-0 rounded-full bg-white text-gray-900 shadow-md";

  return (
    <div className="app-header w-full pb-6 font-arimo text-white">
      <div className="app-stripe" />
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
                  ? DashboardIconBlack
                  : DashboardIconWhite
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
                  ? LeaderboardIconBlack
                  : LeaderboardIconWhite
              }
              alt="leaderboard"
              className="w-4 h-4"
            />
            Leaderboard
          </div>
        </button>
      </div>

      <div className="border-b border-white/10"></div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <h1
          className="text-3xl font-bold font-arimo text-white tracking-wide"
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
            <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
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
              <CustomPeriodButton
                startDate={startDate}
                endDate={endDate}
                onPeriodChange={onPeriodChange}
                onStartDateChange={onStartDateChange}
                onEndDateChange={onEndDateChange}
                buttonClassName={periodBtn(period === "custom")}
              />
            </div>
          </div>

          <div className="flex flex-col">
            <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
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
          <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
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

        <ThemeSwitcher />

        {/* CSV */}
        <div className="flex flex-col">
          <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
            &nbsp;
          </label>

          <button
            onClick={onDownloadCSV}
            className="flex items-center gap-2 bg-csv hover:bg-csv-hover text-white px-4 py-2 rounded-full font-black shadow-lg"
          >
            <img src={DownloadIcon} alt="download" className="w-4 h-4" />
            CSV
          </button>
        </div>

        {/* JSON */}
        <div className="flex flex-col">
          <label className="text-white/85 text-sm font-bold mb-2 tracking-wide">
            &nbsp;
          </label>

          <button
            onClick={onDownloadJSON}
            className="flex items-center gap-2 bg-brand hover:bg-brand-light text-white px-4 py-2 rounded-full font-black shadow-lg"
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