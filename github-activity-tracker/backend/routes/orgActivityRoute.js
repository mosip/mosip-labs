const express = require("express");
const router = express.Router();
const { getOrgActivity } = require("../services/orgActivityService");
const { resolveRoleFilter } = require("../services/userRolesService");
const { resolvePeriodQuery } = require("../utils/dateRange");

router.get("/orgs/:org_id/activity", async (req, res) => {
  const { org_id } = req.params;
  const { role } = req.query;
  const { error: periodError, period, startDate, endDate } = resolvePeriodQuery(req.query);

  if (!org_id || typeof org_id !== "string") {
    return res.status(400).json({ error: "Invalid org_id" });
  }

  if (periodError) {
    return res.status(400).json({ error: periodError });
  }

  try {
    const { error, roleFilter } = await resolveRoleFilter(role);
    if (error) {
      return res.status(400).json({ error });
    }

    const data = await getOrgActivity(org_id, period, roleFilter, startDate, endDate);
    return res.json(data);
  } catch (err) {
    console.error("Error fetching org activity:", err);
    return res.status(500).json({ error: "Failed to fetch org activity" });
  }
});

module.exports = router;