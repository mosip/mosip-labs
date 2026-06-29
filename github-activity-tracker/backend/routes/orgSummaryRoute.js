const express = require('express');
const router = express.Router();
const { getOrgSummary } = require('../services/orgSummaryService');
const { getProjectById } = require('../config/projects');

function resolveProject(req) {
  const project = req.query.project || 'all';
  if (project !== 'all') {
    getProjectById(project);
  }
  return project;
}

router.get('/orgs/:org_id/summary', async (req, res) => {
  try {
    const { period = 'weekly' } = req.query;
    const project = resolveProject(req);

    if (!['daily', 'weekly', 'monthly'].includes(period)) {
      return res.status(400).json({ error: 'Invalid period value' });
    }

    const summary = await getOrgSummary(period, project);
    return res.status(200).json({ ...summary, project });
  } catch (err) {
    if (err.message && err.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: err.message });
    }
    console.error('Error in summary API:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
