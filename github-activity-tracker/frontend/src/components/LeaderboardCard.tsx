import React from "react";

import GoldIcon from "../assets/GoldIcon.svg";
import SilverIcon from "../assets/SilverIcon.svg";
import BronzeIcon from "../assets/BronzeIcon.svg";

interface Leader {
  name: string;
  team: string;
  project: string;
  commits: number;
  prs: number;
  reviews: number;
  total: number;
}

interface LeaderboardCardProps {
  leaders: Leader[];
}

const LeaderboardCard: React.FC<LeaderboardCardProps> = ({ leaders }) => {
  return (
    <div className="space-y-6">
      {(leaders || []).slice(0, 10).map((user, idx) => {
        const rank = idx + 1;

        let badge = null;
        let wrapperClass = "border-2 bg-white";

        if (rank === 1) {
          badge = <img src={GoldIcon} alt="gold" className="w-6 h-6" />;
          wrapperClass = "border-2 bg-[#FEFCE8]";
        } else if (rank === 2) {
          badge = <img src={SilverIcon} alt="silver" className="w-6 h-6" />;
          wrapperClass = "border-2 bg-[#FFFFFF]";
        } else if (rank === 3) {
          badge = <img src={BronzeIcon} alt="bronze" className="w-6 h-6" />;
          wrapperClass = "border-2 bg-[#FFFFFF]";
        }

        return (
          <div
            key={idx}
            className={`rounded-xl p-6 shadow-sm ${wrapperClass}`}
            style={{
              borderColor:
                rank === 1
                  ? "#FFDF20"
                  : rank === 2
                  ? "#D1D5DC"
                  : rank === 3
                  ? "#FFD230"
                  : "#E5E7EB",
            }}
          >
            {/* TOP ROW */}
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-4">
                {rank <= 3 && <div className="mt-1">{badge}</div>}

                {rank > 3 && (
                  <span className="text-gray-500 text-lg font-semibold w-6">
                    {rank}
                  </span>
                )}

                <div>
                  <h2 className="font-semibold text-lg">{user.name}</h2>

                  <p className="text-gray-500 text-sm">
                    {user.team} • {user.project}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="text-2xl font-bold">{user.total}</p>
                <p className="text-gray-400 text-sm">Total</p>
              </div>
            </div>

            {/* METRICS ROW */}
            <div className="flex mt-4 text-sm pl-10 w-full">
              <div className="flex justify-between flex-1 pr-10">
                <span style={{ color: "#4A5565" }}>Commits:</span>
                <span style={{ color: "#155DFC", fontWeight: 600 }}>
                  {user.commits}
                </span>
              </div>

              <div className="flex justify-between flex-1 pr-10">
                <span style={{ color: "#4A5565" }}>PRs:</span>
                <span style={{ color: "#00A63E", fontWeight: 600 }}>
                  {user.prs}
                </span>
              </div>

              <div className="flex justify-between flex-1">
                <span style={{ color: "#4A5565" }}>Reviews:</span>
                <span style={{ color: "#F54900", fontWeight: 600 }}>
                  {user.reviews}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default LeaderboardCard;