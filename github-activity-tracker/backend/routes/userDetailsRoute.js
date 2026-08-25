const express = require('express');
const router = express.Router();
const { getUserDetails } = require('../services/userDetailsService');
const { resolveRoleFilter } = require('../services/userRolesService');
const { resolvePeriodQuery } = require('../utils/dateRange');

// GET /orgs/:org_id/users/:login?period=daily|weekly|monthly|yearly|custom&role=Developer
router.get('/orgs/:org_id/users/:login', async (req, res) => {
  const { org_id, login } = req.params;
  const { role } = req.query;
  const { error: periodError, period, startDate, endDate } = resolvePeriodQuery(req.query);

  if (!login) {
    return res.status(400).json({ error: 'Missing user login' });
  }

  if (periodError) {
    return res.status(400).json({ error: periodError });
  }

  try {
    const { error, roleFilter } = await resolveRoleFilter(role);
    if (error) {
      return res.status(400).json({ error });
    }

    const data = await getUserDetails(org_id, login, period, roleFilter, startDate, endDate);
    return res.json(data);
  } catch (err) {
    console.error('Error in User Details API:', err);
    return res.status(500).json({ error: 'Failed to fetch user details' });
  }
});

module.exports = router;
