const express = require('express');
const router = express.Router();
const { getUserDetails } = require('../services/userDetailsService');

// GET /orgs/:org_id/users/:login?period=daily|weekly|monthly
router.get('/orgs/:org_id/users/:login', async (req, res) => {
  const { org_id, login } = req.params;
  const { period="weekly" } = req.query;

  if (!login) {
    return res.status(400).json({ error: 'Missing user login' });
  }

  if (!['daily', 'weekly', 'monthly'].includes(period)) {
    return res.status(400).json({ error: 'Invalid period value' });
  }

  try {
    const data = await getUserDetails(org_id, login, period);
    return res.json(data);
  } catch (err) {
    console.error('Error in User Details API:', err);
    return res.status(500).json({ error: 'Failed to fetch user details' });
  }
});

module.exports = router;