const express = require("express");
const router = express.Router();

const { getLeaderboard } = require("../services/leaderBoardService");
const { resolveRoleFilter } = require("../services/userRolesService");

router.get("/orgs/:org_id/leaderboard", async (req, res) => {
  try {
    const { org_id } = req.params;

    const period = req.query.period || "weekly";
    const limit = parseInt(req.query.limit) || 10;
    const { role } = req.query;

    if (!org_id || typeof org_id !== "string") {
      return res.status(400).json({ error: "Invalid org_id" });
    }

    if (!["daily", "weekly", "monthly", "yearly", "all"].includes(period)) {
      return res.status(400).json({ error: "Invalid period value" });
    }

    const { error, roleFilter } = await resolveRoleFilter(role);
    if (error) {
      return res.status(400).json({ error });
    }

    const data = await getLeaderboard(org_id, period, limit, roleFilter);

    return res.status(200).json(data);
  } catch (error) {
    console.error("Leaderboard API error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;