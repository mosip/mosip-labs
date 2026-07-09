const express = require('express');
const router = express.Router();
const { getOrgSummary } = require('../services/orgSummaryService');
const { isValidUserRole } = require('../config/userRoles');

router.get('/orgs/:org_id/summary', async (req, res) => {
  try {
    const { org_id } = req.params;
    const { period = 'weekly', role } = req.query;

    if (!org_id) {
      return res.status(400).json({ error: 'Invalid org_id' });
    }

    if (!['daily', 'weekly', 'monthly', 'yearly'].includes(period)) {
      return res.status(400).json({ error: 'Invalid period value' });
    }

    if (role && role !== 'all' && !(await isValidUserRole(role))) {
      return res.status(400).json({ error: 'Invalid role value' });
    }

    const roleFilter = role && role !== 'all' ? role : null;
    const summary = await getOrgSummary(org_id, period, roleFilter);

    return res.status(200).json(summary);
  } catch (err) {
    console.error('Error in summary API:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;