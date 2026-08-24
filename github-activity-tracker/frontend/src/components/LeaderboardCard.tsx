import React from "react";

import GoldIcon from "../assets/GoldIcon.svg";
import SilverIcon from "../assets/SilverIcon.svg";
import BronzeIcon from "../assets/BronzeIcon.svg";

interface Leader {
  name: string;
  login?: string;
  team: string;
  project: string;
  prs: number;
  reviews: number;
  issues: number;
  total: number;
}

interface LeaderboardCardProps {
  leaders: Leader[];
}

const LeaderboardCard: React.FC<LeaderboardCardProps> = ({ leaders }) => {
  return (
    <div className="space-y-4">
      {(leaders || []).slice(0, 10).map((user, idx) => {
        const rank = idx + 1;

        let badge = null;
        let wrapperClass = "bg-[#f8fbff] border border-[#d5e4f0]";

        if (rank === 1) {
          badge = <img src={GoldIcon} alt="gold" className="w-7 h-7" />;
          wrapperClass = "bg-[#f3f9ff] border border-sky-200";
        } else if (rank === 2) {
          badge = <img src={SilverIcon} alt="silver" className="w-7 h-7" />;
          wrapperClass = "bg-[#e8f4fb] border border-sky-100";
        } else if (rank === 3) {
          badge = <img src={BronzeIcon} alt="bronze" className="w-7 h-7" />;
          wrapperClass = "bg-[#fff3e8] border border-orange-100";
        }

        return (
          <div
            key={idx}
            className={`rounded-[24px] p-6 shadow-lg ${wrapperClass}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-4">
                {rank <= 3 && <div className="mt-1">{badge}</div>}

                {rank > 3 && (
                  <span className="w-9 h-9 rounded-full bg-sky-500 text-white flex items-center justify-center text-sm font-black">
                    {rank}
                  </span>
                )}

                <div>
                  <h2 className="font-black text-lg text-stone-800">{user.name}</h2>
                  <p className="text-stone-500 text-sm">
                    {user.login ? `@${user.login}` : `${user.team} • ${user.project}`}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="text-3xl font-black text-sky-700">{user.total}</p>
                <p className="text-stone-400 text-xs font-bold tracking-widest uppercase">
                  Total
                </p>
              </div>
            </div>

            <div className="flex mt-4 text-sm pl-12 w-full gap-3">
              <div className="flex justify-between flex-1 rounded-full bg-[#e8f4fb] px-4 py-2">
                <span className="text-sky-700 font-bold">PRs</span>
                <span className="text-sky-800 font-black">{user.prs}</span>
              </div>
              <div className="flex justify-between flex-1 rounded-full bg-[#fff3e8] px-4 py-2">
                <span className="text-orange-800 font-bold">Reviews</span>
                <span className="text-orange-900 font-black">{user.reviews}</span>
              </div>
              <div className="flex justify-between flex-1 rounded-full bg-[#eeedff] px-4 py-2">
                <span className="text-indigo-800 font-bold">Issues</span>
                <span className="text-indigo-900 font-black">{user.issues}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default LeaderboardCard;
