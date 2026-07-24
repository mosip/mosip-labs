/**
 * Route: POST /admin/sync/issues
 * Syncs GitHub issues for every repository in the repos table. No body required.
 * Uses GitHub Search API; 422 may mean the token has no access to a repo.
 */
const express = require('express');
const pool = require('../db/dbPool');
const { syncIssues } = require('../services/prSyncService');
const { HTTP, GITHUB, STATUS } = require('../config/errorCodes');
const { DELAY_BETWEEN_REPOS_MS } = require('../config/syncConfig');

const router = express.Router();

router.post('/admin/sync/issues', async (req, res) => {
  try {
    const reposResult = await pool.query(
      'SELECT github_repo_id, owner, name, full_name FROM repos ORDER BY github_repo_id'
    );

    const repos = reposResult.rows;
    const totalRepos = repos.length;

    if (totalRepos === 0) {
      return res.json({
        status: STATUS.SUCCESS,
        message: 'No repositories found in database',
        repos_processed: 0,
        issues_processed: 0,
      });
    }

    let totalIssuesProcessed = 0;
    let reposProcessed = 0;

    for (let i = 0; i < repos.length; i++) {
      const repo = repos[i];
      const repoId = repo.github_repo_id;
      const repoName = repo.full_name || `${repo.owner}/${repo.name}`;

      try {
        console.log(`[${i + 1}/${totalRepos}] Syncing issues for ${repoName} (ID: ${repoId})`);
        const issuesProcessed = await syncIssues(repoId);
        totalIssuesProcessed += issuesProcessed;
        reposProcessed += 1;
        console.log(`✓ Completed ${repoName}: ${issuesProcessed} issues`);
      } catch (repoError) {
        console.error(`✗ Error syncing issues for ${repoName}:`, repoError.message);
        continue;
      }

      if (i < repos.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, DELAY_BETWEEN_REPOS_MS));
      }
    }

    return res.json({
      status: STATUS.SUCCESS,
      repos_processed: reposProcessed,
      total_repos: totalRepos,
      issues_processed: totalIssuesProcessed,
    });
  } catch (error) {
    console.error('Error syncing issues:', error);
    console.error('Error stack:', error.stack);

    if (error.message && error.message.includes('not found')) {
      return res.status(HTTP.NOT_FOUND).json({
        status: STATUS.ERROR,
        message: error.message,
        issues_processed: 0,
      });
    }

    const isValidationFailed =
      error.statusCode === HTTP.UNPROCESSABLE_ENTITY ||
      error.response?.status === GITHUB.VALIDATION_FAILED;
    if (isValidationFailed) {
      const message =
        error.message ||
        error.response?.data?.message ||
        'GitHub rejected the search request (validation failed). Your token may not have access to this repository.';
      return res.status(HTTP.UNPROCESSABLE_ENTITY).json({
        status: STATUS.ERROR,
        message,
        issues_processed: 0,
      });
    }

    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to sync issues',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
      issues_processed: 0,
    });
  }
});

module.exports = router;
