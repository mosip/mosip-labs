import React, { useEffect, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { fetchOrgUsers } from "../lib/api";
import type { PeriodValue } from "../lib/periods";

type SortField = "prs" | "reviews" | "issues";
type SortOrder = "asc" | "desc";
const UserIcon = () => (
  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-2xl">
    👤
  </div>
);

interface TeamMembersProps {
  org: string;
  role: string;
  period: PeriodValue;
  startDate?: string;
  endDate?: string;
  onSelectUser?: (name: string) => void;
}

const getDiffColor = (diff: number) => {
  if (diff > 0) return "#00A63E";
  if (diff < 0) return "#E7000B";
  return "#155DFC";
};

interface SortableHeaderProps {
  label: string;
  field: SortField;
  sortBy: SortField | null;
  sortOrder: SortOrder;
  onSort: (field: SortField, order: SortOrder) => void;
}

const SortableHeader: React.FC<SortableHeaderProps> = ({
  label,
  field,
  sortBy,
  sortOrder,
  onSort,
}) => {
  const isActive = sortBy === field;

  return (
    <th className="px-4 py-3 font-semibold text-center">
      <div className="flex items-center justify-center gap-1">
        <span>{label}</span>
        <div className="flex flex-col">
          <button
            type="button"
            onClick={() => onSort(field, "asc")}
            className={`p-0.5 rounded hover:bg-gray-200 transition ${
              isActive && sortOrder === "asc"
                ? "text-blue-600 bg-blue-50"
                : "text-gray-400"
            }`}
            aria-label={`Sort ${label} ascending`}
          >
            <ArrowUp size={14} />
          </button>
          <button
            type="button"
            onClick={() => onSort(field, "desc")}
            className={`p-0.5 rounded hover:bg-gray-200 transition ${
              isActive && sortOrder === "desc"
                ? "text-blue-600 bg-blue-50"
                : "text-gray-400"
            }`}
            aria-label={`Sort ${label} descending`}
          >
            <ArrowDown size={14} />
          </button>
        </div>
      </div>
    </th>
  );
};
const TeamMembers: React.FC<TeamMembersProps> = ({
  org,
  role,
  period,
  startDate,
  endDate,
  onSelectUser,
}) => {
  const [members, setMembers] = useState<any[]>([]);
  const [userSearchTerm, setUserSearchTerm] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [sortBy, setSortBy] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  useEffect(() => {
    if (period === "custom" && (!startDate || !endDate || startDate > endDate)) return;

    async function loadUsers() {
      try {
        const data = await fetchOrgUsers(
          org,
          period,
          page,
          limit,
          role,
          appliedSearch,
          sortBy,
          sortOrder,
          startDate,
          endDate,
        );

        if (Array.isArray(data)) {
          // backend returned plain array
          setMembers(data);
          setTotalUsers(data.length);
          setTotalPages(1);
        } else {
          // backend returned pagination object
          setMembers(data.users || []);
          setTotalUsers(data.totalUsers || 0);
          setTotalPages(data.totalPages || 1);
        }
      } catch (err) {
        console.error("Error loading team members:", err);
        setMembers([]);
        setTotalUsers(0);
        setTotalPages(1);
        setPage(1);
      }
    }

    loadUsers();
  }, [org, period, page, limit, role, appliedSearch, sortBy, sortOrder, startDate, endDate]);
  useEffect(() => {
    setPage(1);
  }, [org, role, period, startDate, endDate]);

  const handleSearch = () => {
    setPage(1);
    setAppliedSearch(userSearchTerm.trim());
  };

  const handleSort = (field: SortField, order: SortOrder) => {
    setSortBy(field);
    setSortOrder(order);
    setPage(1);
  };
  const startItem = totalUsers === 0 ? 0 : (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, totalUsers);

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border mb-8 font-arimo">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Team Members</h2>
        <div className="flex gap-2 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Search users..."
            value={userSearchTerm}
            onChange={(e) => setUserSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="flex-1 sm:w-64 border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-1 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            Search
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full table-fixed">
          <colgroup>
            <col className="w-[25%]" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
          </colgroup>
          <thead>
            <tr className="text-left text-gray-600 border-b bg-gray-50">
              <th className="px-4 py-3 font-semibold">Team Member</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <SortableHeader
                label="PRs"
                field="prs"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <th className="px-4 py-3 font-semibold text-center">File Changes</th>
              <SortableHeader
                label="Reviews"
                field="reviews"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <SortableHeader
                label="Issues"
                field="issues"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
            </tr>
          </thead>

          <tbody>
            {members.map((m, index) => (
              <tr
                key={m.assignment_id ?? `${m.login}-${index}`}
                className="border-b last:border-0 cursor-pointer hover:bg-gray-50 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                onClick={() => onSelectUser?.(m.login)}
                role={onSelectUser ? "button" : undefined}
                tabIndex={onSelectUser ? 0 : undefined}
                aria-label={
                  onSelectUser
                    ? `View profile for ${m.name || m.login}`
                    : undefined
                }
                onKeyDown={(e) => {
                  if (!onSelectUser) return;
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectUser(m.login);
                  }
                }}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                  <UserIcon />
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-gray-900">
                        {m.name || m.login}
                      </p>
                      <p className="truncate text-gray-500 text-sm">{m.login}</p>
                    </div>
                  </div>
                </td>

                <td className="px-4 py-4 text-left text-gray-700">
                  {m.role || "—"}
                  {m.role && m.is_active === false && (
                    <span className="ml-2 text-xs text-gray-500">(inactive)</span>
                  )}
                </td>

                <td className="px-4 py-4 text-center">
                  <div
                    className="font-semibold"
                    style={{ color: getDiffColor(m.diffPRs) }}
                  >
                    {m.prs}
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: getDiffColor(m.diffPRs) }}
                  >
                    ({m.diffPRs > 0 ? "+" : ""}
                    {m.diffPRs})
                  </div>
                </td>

                <td className="px-4 py-4 text-center font-semibold text-gray-900">
                  {m.pr_files_changed ?? 0}
                </td>

                <td className="px-4 py-4 text-center">
                  <div
                    className="font-semibold"
                    style={{ color: getDiffColor(m.diffReviews) }}
                  >
                    {m.reviews}
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: getDiffColor(m.diffReviews) }}
                  >
                    ({m.diffReviews > 0 ? "+" : ""}
                    {m.diffReviews})
                  </div>
                </td>

                <td className="px-4 py-4 text-center">
                  <div
                    className="font-semibold"
                    style={{ color: getDiffColor(m.diffIssues) }}
                  >
                    {m.issues ?? 0}
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: getDiffColor(m.diffIssues ?? 0) }}
                  >
                    ({(m.diffIssues ?? 0) > 0 ? "+" : ""}
                    {m.diffIssues ?? 0})
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}

      <div className="flex items-center justify-between mt-6 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <span>Items per page</span>

          <select
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setPage(1);
            }}
            className="border rounded px-2 py-1"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div>
          {startItem}–{endItem} of {totalUsers} items
        </div>

        <div className="flex items-center gap-3">
          <button
            disabled={page === 1}
            onClick={() => setPage(1)}
            className="disabled:opacity-30"
          >
            ⏮
          </button>

          <button
            disabled={page === 1}
            onClick={() => setPage((prev) => prev - 1)}
            className="disabled:opacity-30"
          >
            ◀ Previous
          </button>

          <span className="border px-3 py-1 rounded">{page}</span>

          <span>of {totalPages}</span>

          <button
            disabled={page === totalPages}
            onClick={() => setPage((prev) => prev + 1)}
            className="disabled:opacity-30"
          >
            Next ▶
          </button>

          <button
            disabled={page === totalPages}
            onClick={() => setPage(totalPages)}
            className="disabled:opacity-30"
          >
            ⏭
          </button>
        </div>
      </div>
    </div>
  );
};

export default TeamMembers;
