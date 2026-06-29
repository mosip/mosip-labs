const express = require('express');
const router = express.Router();
const { getUserDetails } = require('../services/userDetailsService');
const { getProjectById } = require('../config/projects');

function resolveProject(req) {
  const project = req.query.project || 'all';
  if (project !== 'all') {
    getProjectById(project);
  }
  return project;
}

router.get('/orgs/:org_id/users/:login', async (req, res) => {
  const { login } = req.params;
  const { period = 'weekly' } = req.query;
  const project = resolveProject(req);

  if (!login) {
    return res.status(400).json({ error: 'Missing user login' });
  }

  if (!['daily', 'weekly', 'monthly'].includes(period)) {
    return res.status(400).json({ error: 'Invalid period value' });
  }

  try {
    const data = await getUserDetails(login, period, project);
    return res.json(data);
  } catch (err) {
    if (err.message && err.message.startsWith('Unknown project')) {
      return res.status(400).json({ error: err.message });
    }
    if (err.message === 'User not found') {
      return res.status(404).json({ error: err.message });
    }
    console.error('Error in User Details API:', err);
    return res.status(500).json({ error: 'Failed to fetch user details' });
  }
});

module.exports = router;
