const express = require("express");
const router = express.Router();

const { getLeaderboard } = require("../services/leaderBoardService");

router.get("/orgs/:org_id/leaderboard", async (req, res) => {
  try {
    const { org_id } = req.params;

    const period = req.query.period || "weekly";
    const limit = parseInt(req.query.limit) || 10;

    if (!org_id || typeof org_id !== "string") {
      return res.status(400).json({ error: "Invalid org_id" });
    }

    const data = await getLeaderboard(org_id, period, limit);

    return res.status(200).json(data);
  } catch (error) {
    console.error("Leaderboard API error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;