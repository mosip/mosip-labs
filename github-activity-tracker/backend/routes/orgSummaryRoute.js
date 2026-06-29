const express = require('express');
const router = express.Router();
const { getOrgSummary } = require('../services/orgSummaryService');

router.get('/orgs/:org_id/summary', async (req, res) => {
  try {
    const { org_id } = req.params;
    const { period = 'weekly' } = req.query;

    if (!org_id) {
      return res.status(400).json({ error: 'Invalid org_id' });
    }

    if (!['daily', 'weekly', 'monthly'].includes(period)) {
      return res.status(400).json({ error: 'Invalid period value' });
    }

    const summary = await getOrgSummary(period);

    return res.status(200).json(summary);
  } catch (err) {
    console.error('Error in summary API:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;