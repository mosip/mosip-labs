const express = require("express");
const router = express.Router();

const { getOrgUsers } = require("../services/orgUsersService");
const { isValidUserRole } = require("../services/userRolesService");
const { resolvePeriodQuery } = require("../utils/dateRange");

router.get("/orgs/:org_id/users", async (req, res) => {
  try {
    const { org_id } = req.params;

    const { error: periodError, period, startDate, endDate } = resolvePeriodQuery(req.query);
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const { role, search, sortBy, sortOrder } = req.query;

    if (!org_id || typeof org_id !== "string") {
      return res.status(400).json({ error: "Invalid org_id" });
    }

    if (periodError) {
      return res.status(400).json({ error: periodError });
    }

    if (role && role !== "all" && !(await isValidUserRole(role))) {
      return res.status(400).json({ error: "Invalid role value" });
    }

    const roleFilter = role && role !== "all" ? role : null;

    const searchFilter =
      typeof search === "string" && search.trim() ? search.trim() : null;

    const allowedSortFields = ["prs", "reviews", "issues"];
    const sortByFilter =
      typeof sortBy === "string" && allowedSortFields.includes(sortBy)
        ? sortBy
        : null;
    const sortOrderFilter =
      sortOrder === "asc" || sortOrder === "desc" ? sortOrder : "desc";

    const users = await getOrgUsers(
      org_id,
      period,
      page,
      limit,
      roleFilter,
      searchFilter,
      sortByFilter,
      sortOrderFilter,
      startDate,
      endDate,
    );

    return res.status(200).json(users);

  } catch (error) {
    console.error("Error fetching org users:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

module.exports = router;