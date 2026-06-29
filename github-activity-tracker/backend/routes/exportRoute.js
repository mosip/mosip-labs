const express = require('express');
const { getExportData, toCsv } = require('../services/exportService');
const { getProjectById } = require('../config/projects');

const router = express.Router();

router.get('/orgs/:org_id/export', async (req, res) => {
  const { period = 'weekly', format = 'json' } = req.query;
  const project = req.query.project || 'all';

  if (!['daily', 'weekly', 'monthly'].includes(period)) {
    return res.status(400).json({ error: 'Invalid period value' });
  }

  if (!['json', 'csv'].includes(format)) {
    return res.status(400).json({ error: 'Invalid format. Use json or csv' });
  }

  try {
    if (project !== 'all') {
      getProjectById(project);
    }

    const data = await getExportData(project, period);

    if (format === 'csv') {
      const csv = toCsv(data);
      const filename = `github-activity-${project}-${period}.csv`;
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.send(csv);
    }

    return res.json(data);
  } catch (err) {
    if (err.message && err.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: err.message });
    }
    console.error('Export error:', err);
    return res.status(500).json({ error: 'Failed to export data' });
  }
});

module.exports = router;
