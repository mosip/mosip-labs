const express = require('express');
const { getProjectListForApi } = require('../config/projects');

const router = express.Router();

router.get('/projects', (req, res) => {
  try {
    const projects = getProjectListForApi();
    return res.json({ projects });
  } catch (error) {
    console.error('Error loading projects:', error);
    return res.status(500).json({ error: 'Failed to load project configuration' });
  }
});

module.exports = router;
