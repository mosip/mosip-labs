const express = require("express");
const router = express.Router();
const { getLeaderboard } = require("../services/leaderBoardService");
const { getProjectById } = require("../config/projects");

function resolveProject(req) {
  const project = req.query.project || 'all';
  if (project !== 'all') {
    getProjectById(project);
  }
  return project;
}

router.get("/orgs/:org_id/leaderboard", async (req, res) => {
  try {
    const period = req.query.period || "weekly";
    const limit = parseInt(req.query.limit) || 10;
    const project = resolveProject(req);

    if (!["daily", "weekly", "monthly", "all"].includes(period)) {
      return res.status(400).json({ error: "Invalid period value" });
    }

    const data = await getLeaderboard(project, period, limit);
    return res.status(200).json(data);
  } catch (error) {
    if (error.message && error.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: error.message });
    }
    console.error("Leaderboard API error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;
