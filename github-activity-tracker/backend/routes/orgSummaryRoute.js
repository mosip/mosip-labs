const express = require('express');
const router = express.Router();
const { getOrgSummary } = require('../services/orgSummaryService');
const { resolveRoleFilter } = require('../services/userRolesService');
const { resolvePeriodQuery } = require('../utils/dateRange');

router.get('/orgs/:org_id/summary', async (req, res) => {
  try {
    const { org_id } = req.params;
    const { role } = req.query;
    const { error: periodError, period, startDate, endDate } = resolvePeriodQuery(req.query);

    if (!org_id) {
      return res.status(400).json({ error: 'Invalid org_id' });
    }

    if (periodError) {
      return res.status(400).json({ error: periodError });
    }

    const { error, roleFilter } = await resolveRoleFilter(role);
    if (error) {
      return res.status(400).json({ error });
    }

    const summary = await getOrgSummary(org_id, period, roleFilter, startDate, endDate);

    return res.status(200).json(summary);
  } catch (err) {
    console.error('Error in summary API:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;