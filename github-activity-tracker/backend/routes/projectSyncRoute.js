/**
 * Route: POST /admin/sync/all
 * Syncs repositories, commits, PRs, and reviews for every configured project.
 */
const express = require('express');
const { syncAllProjects } = require('../services/projectSyncService');
const { HTTP, STATUS } = require('../config/errorCodes');

const router = express.Router();

router.post('/admin/sync/all', async (req, res) => {
  try {
    const results = await syncAllProjects();

    return res.json({
      status: STATUS.SUCCESS,
      projects_processed: results.length,
      results,
    });
  } catch (error) {
    console.error('Error syncing all projects:', error);
    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to sync all projects',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
    });
  }
});

module.exports = router;
