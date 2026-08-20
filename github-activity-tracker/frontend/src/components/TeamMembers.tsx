import React, { useEffect, useState } from "react";
import { fetchOrgUsers } from "../lib/api";

const UserIcon = () => (
  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-2xl">
    👤
  </div>
);

interface TeamMembersProps {
  team: string;
  project: string;
  period: "daily" | "weekly" | "monthly";
  onSelectUser?: (name: string) => void;
}

const getDiffColor = (diff: number) => {
  if (diff > 0) return "#00A63E";
  if (diff < 0) return "#E7000B";
  return "#155DFC";
};

const TeamMembers: React.FC<TeamMembersProps> = ({
  team,
  project,
  period,
  onSelectUser,
}) => {
  const [members, setMembers] = useState<any[]>([]);

  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    async function loadUsers() {
      try {
        const data = await fetchOrgUsers("mosip", period, page, limit);

        console.log("API RESPONSE:", data);

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
      }
    }

    loadUsers();
  }, [period, page, limit]);

  const filtered = members.filter((m) => {
    const matchTeam =
      team === "all" || (m.team || "").toLowerCase() === team.toLowerCase();

    const matchProject =
      project === "all" ||
      (m.project || "").toLowerCase() === project.toLowerCase();

    return matchTeam && matchProject;
  });

  const startItem = totalUsers === 0 ? 0 : (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, totalUsers);

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border mb-8 font-arimo">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Team Members</h2>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-gray-600 border-b bg-gray-50">
              <th className="pb-3 font-semibold">Team Member</th>
              <th className="pb-3 font-semibold">Team</th>
              <th className="pb-3 font-semibold">Project</th>
              <th className="pb-3 font-semibold">Role</th>
              <th className="pb-3 font-semibold">Commits</th>
              <th className="pb-3 font-semibold">PRs</th>
              <th className="pb-3 font-semibold">Reviews</th>
            </tr>
          </thead>

          <tbody>
            {filtered.map((m, index) => (
              <tr
                key={index}
                className="border-b last:border-0 cursor-pointer hover:bg-gray-50 transition"
                onClick={() => onSelectUser?.(m.login)}
              >
                <td className="py-4 flex items-center gap-3">
                  <UserIcon />
                  <div>
                    <p className="font-semibold text-gray-900">{m.login}</p>
                    <p className="text-gray-500 text-sm">{m.email || "—"}</p>
                  </div>
                </td>

                <td className="text-gray-700">{m.team || "—"}</td>
                <td className="text-gray-700">{m.project || "—"}</td>
                <td className="text-gray-700">{m.role || "—"}</td>

                <td className="text-center">
                  <div
                    className="font-semibold"
                    style={{ color: getDiffColor(m.diffCommits) }}
                  >
                    {m.commits}
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: getDiffColor(m.diffCommits) }}
                  >
                    ({m.diffCommits > 0 ? "+" : ""}
                    {m.diffCommits})
                  </div>
                </td>

                <td className="text-center">
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

                <td className="text-center">
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
