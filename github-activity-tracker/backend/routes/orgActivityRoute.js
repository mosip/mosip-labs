const express = require("express");
const router = express.Router();
const { getOrgActivity } = require("../services/orgActivityService");

router.get("/orgs/:org_id/activity", async (req, res) => {
  const { org_id } = req.params;
  const { period = "weekly" } = req.query;

  try {
    const data = await getOrgActivity(period);
    return res.json(data);
  } catch (err) {
    console.error("Error fetching org activity:", err);
    return res.status(500).json({ error: "Failed to fetch org activity" });
  }
});

module.exports = router;