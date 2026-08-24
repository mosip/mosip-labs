const express = require("express");
const router = express.Router();

const { getLeaderboard } = require("../services/leaderBoardService");
const { resolveRoleFilter } = require("../services/userRolesService");
const { resolvePeriodQuery } = require("../utils/dateRange");

router.get("/orgs/:org_id/leaderboard", async (req, res) => {
  try {
    const { org_id } = req.params;

    const { error: periodError, period, startDate, endDate } = resolvePeriodQuery(req.query, {
      allowAll: true,
    });
    const limit = parseInt(req.query.limit) || 10;
    const { role } = req.query;

    if (!org_id || typeof org_id !== "string") {
      return res.status(400).json({ error: "Invalid org_id" });
    }

    if (periodError) {
      return res.status(400).json({ error: periodError });
    }

    const { error, roleFilter } = await resolveRoleFilter(role);
    if (error) {
      return res.status(400).json({ error });
    }

    const data = await getLeaderboard(org_id, period, limit, roleFilter, startDate, endDate);

    return res.status(200).json(data);
  } catch (error) {
    console.error("Leaderboard API error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;