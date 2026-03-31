const express = require("express");
const router = express.Router();
const { getOrgActivity } = require("../services/orgActivityService");

router.get("/orgs/:org_id/activity", async (req, res) => {
  const { org_id } = req.params;
  const { period = "weekly" } = req.query;

  if (!["daily", "weekly", "monthly"].includes(period)) {
    return res.status(400).json({ error: "Invalid period value" });
  }

  try {
    const data = await getOrgActivity(period);
    return res.json(data);
  } catch (err) {
    console.error("Error fetching org activity:", err);
    return res.status(500).json({ error: "Failed to fetch org activity" });
  }
});

module.exports = router;