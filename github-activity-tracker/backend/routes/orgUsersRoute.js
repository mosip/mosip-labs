const express = require("express");
const router = express.Router();

const { getOrgUsers } = require("../services/orgUsersService");

router.get("/orgs/:org_id/users", async (req, res) => {
  try {
    const { org_id } = req.params;

    const period = req.query.period || "weekly";
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;

    if (!org_id || typeof org_id !== "string") {
      return res.status(400).json({ error: "Invalid org_id" });
    }

    if (!["daily", "weekly", "monthly"].includes(period)) {
      return res.status(400).json({ error: "Invalid period value" });
    }

    // pass pagination to service
    const users = await getOrgUsers(org_id, period, page, limit);

    return res.status(200).json(users);

  } catch (error) {
    console.error("Error fetching org users:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;