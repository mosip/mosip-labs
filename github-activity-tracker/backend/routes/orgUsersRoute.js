const express = require("express");
const router = express.Router();
const { getOrgUsers } = require("../services/orgUsersService");
const { getProjectById } = require("../config/projects");

function resolveProject(req) {
  const project = req.query.project || 'all';
  if (project !== 'all') {
    getProjectById(project);
  }
  return project;
}

router.get("/orgs/:org_id/users", async (req, res) => {
  try {
    const period = req.query.period || "weekly";
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const project = resolveProject(req);

    if (!["daily", "weekly", "monthly"].includes(period)) {
      return res.status(400).json({ error: "Invalid period value" });
    }

    const users = await getOrgUsers(project, period, page, limit);
    return res.status(200).json(users);
  } catch (error) {
    if (error.message && error.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: error.message });
    }
    console.error("Error fetching org users:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;
