/**
 * Route: POST /admin/sync/repos
 * Syncs all public repositories for a GitHub organization into the repos table.
 * Body: { "org": "owner", "project": "project_id" } or { "project": "project_id" }.
 */
const express = require('express');
const { syncRepos } = require('../services/syncRepos');
const { getProjectById } = require('../config/projects');
const { HTTP, STATUS } = require('../config/errorCodes');

const router = express.Router();

router.post('/admin/sync/repos', async (req, res) => {
  const { org, project: projectId } = req.body || {};

  if (!projectId) {
    return res.status(HTTP.BAD_REQUEST).json({
      status: STATUS.ERROR,
      message: 'Missing required field: project',
      repos_processed: 0,
    });
  }

  let project;
  try {
    project = getProjectById(projectId);
  } catch (err) {
    return res.status(HTTP.BAD_REQUEST).json({
      status: STATUS.ERROR,
      message: err.message,
      repos_processed: 0,
    });
  }

  if (!project) {
    return res.status(HTTP.BAD_REQUEST).json({
      status: STATUS.ERROR,
      message: 'A concrete project id is required',
      repos_processed: 0,
    });
  }

  if (org && !project.organizations.includes(org.trim().toLowerCase())) {
    return res.status(HTTP.BAD_REQUEST).json({
      status: STATUS.ERROR,
      message: `Organization ${org} is not configured for project ${project.id}`,
      repos_processed: 0,
    });
  }

  const orgsToSync = org ? [org.trim().toLowerCase()] : project.organizations;

  try {
    let reposProcessed = 0;
    for (const orgLogin of orgsToSync) {
      reposProcessed += await syncRepos(orgLogin, project.id);
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
