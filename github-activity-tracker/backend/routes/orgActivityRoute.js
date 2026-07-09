const express = require("express");
const router = express.Router();
const { getOrgActivity } = require("../services/orgActivityService");
const { isValidUserRole } = require("../config/userRoles");

router.get("/orgs/:org_id/activity", async (req, res) => {
  const { org_id } = req.params;
  const { period = "weekly", role } = req.query;

  if (!org_id || typeof org_id !== "string") {
    return res.status(400).json({ error: "Invalid org_id" });
  }

  if (!["daily", "weekly", "monthly", "yearly"].includes(period)) {
    return res.status(400).json({ error: "Invalid period value" });
  }

  if (role && role !== "all" && !(await isValidUserRole(role))) {
    return res.status(400).json({ error: "Invalid role value" });
  }

  try {
    const roleFilter = role && role !== "all" ? role : null;
    const data = await getOrgActivity(org_id, period, roleFilter);
    return res.json(data);
  } catch (err) {
    console.error("Error fetching org activity:", err);
    return res.status(500).json({ error: "Failed to fetch org activity" });
  }
});

module.exports = router;