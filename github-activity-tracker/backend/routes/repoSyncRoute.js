/**
 * Route: POST /admin/sync/repos
 * Syncs all public repositories for a GitHub organization into the repos table.
 * Uses GITHUB_ORG from environment (supports comma-separated orgs);
 * request body org is a backward-compatible fallback.
 */
const express = require('express');
const { syncRepos } = require('../services/syncRepos');
const { HTTP, STATUS } = require('../config/errorCodes');

const router = express.Router();

router.post('/admin/sync/repos', async (req, res) => {
  const { org: orgFromBody } = req.body || {};
  const configuredOrgs = (process.env.GITHUB_ORG || orgFromBody || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);

  if (configuredOrgs.length === 0) {
    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Missing required organization configuration: set GITHUB_ORG in environment',
      repos_processed: 0,
    });
  }

  try {
    let reposProcessed = 0;
    for (const org of configuredOrgs) {
      reposProcessed += await syncRepos(org);
    }

    return res.json({
      status: STATUS.SUCCESS,
      repos_processed: reposProcessed,
    });
  } catch (error) {
    console.error('Error syncing repositories:', error);
    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to sync repositories',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
      repos_processed: 0,
    });
  }
});

module.exports = router;
