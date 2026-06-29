const express = require("express");
const router = express.Router();
const { getOrgActivity } = require("../services/orgActivityService");
const { getProjectById } = require("../config/projects");

function resolveProject(req) {
  const project = req.query.project || 'all';
  if (project !== 'all') {
    getProjectById(project);
  }
  return project;
}

router.get("/orgs/:org_id/activity", async (req, res) => {
  const { period = "weekly" } = req.query;
  const project = resolveProject(req);

  if (!["daily", "weekly", "monthly"].includes(period)) {
    return res.status(400).json({ error: "Invalid period value" });
  }

  try {
    const data = await getOrgActivity(period, project);
    return res.json({ ...data, project });
  } catch (err) {
    if (err.message && err.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: err.message });
    }
    console.error("Error fetching org activity:", err);
    return res.status(500).json({ error: "Failed to fetch org activity" });
  }
});

module.exports = router;
