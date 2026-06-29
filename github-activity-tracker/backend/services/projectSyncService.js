const pool = require('../db/dbPool');
const { getProjects } = require('../config/projects');
const { syncRepos } = require('./syncRepos');
const { syncCommits } = require('./commitSyncService');
const { syncPRs } = require('./prSyncService');
const { syncReviews } = require('./reviewSyncService');
const { DELAY_BETWEEN_REPOS_MS } = require('../config/syncConfig');

async function getReposForProject(projectId) {
  const result = await pool.query(
    `SELECT github_repo_id, owner, name, full_name
     FROM repos
     WHERE project_id = $1
     ORDER BY github_repo_id`,
    [projectId]
  );
  return result.rows;
}

async function syncCommitsForProject(projectId) {
  const repos = await getReposForProject(projectId);
  let commitsProcessed = 0;
  let reposProcessed = 0;

  for (let i = 0; i < repos.length; i++) {
    const repo = repos[i];
    const repoName = repo.full_name || `${repo.owner}/${repo.name}`;

    try {
      console.log(`[${projectId}] Syncing commits for ${repoName}`);
      commitsProcessed += await syncCommits(repo.github_repo_id);
      reposProcessed += 1;
    } catch (err) {
      console.error(`[${projectId}] Error syncing commits for ${repoName}:`, err.message);
    }

    if (i < repos.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, DELAY_BETWEEN_REPOS_MS));
    }
  }

  return { reposProcessed, commitsProcessed, totalRepos: repos.length };
}

async function syncPRsForProject(projectId) {
  const repos = await getReposForProject(projectId);
  let prsProcessed = 0;
  let reposProcessed = 0;

  for (let i = 0; i < repos.length; i++) {
    const repo = repos[i];
    const repoName = repo.full_name || `${repo.owner}/${repo.name}`;

    try {
      console.log(`[${projectId}] Syncing PRs for ${repoName}`);
      prsProcessed += await syncPRs(repo.github_repo_id);
      reposProcessed += 1;
    } catch (err) {
      console.error(`[${projectId}] Error syncing PRs for ${repoName}:`, err.message);
    }

    if (i < repos.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, DELAY_BETWEEN_REPOS_MS));
    }
  }

  return { reposProcessed, prsProcessed, totalRepos: repos.length };
}

async function syncReviewsForProject(projectId) {
  const repos = await getReposForProject(projectId);
  let reviewsProcessed = 0;
  let reposProcessed = 0;

  for (let i = 0; i < repos.length; i++) {
    const repo = repos[i];
    const repoName = repo.full_name || `${repo.owner}/${repo.name}`;

    try {
      console.log(`[${projectId}] Syncing reviews for ${repoName}`);
      reviewsProcessed += await syncReviews(repo.github_repo_id);
      reposProcessed += 1;
    } catch (err) {
      console.error(`[${projectId}] Error syncing reviews for ${repoName}:`, err.message);
    }

    if (i < repos.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, DELAY_BETWEEN_REPOS_MS));
    }
  }

  return { reposProcessed, reviewsProcessed, totalRepos: repos.length };
}

/**
 * Sync repositories, commits, PRs, and reviews for a single configured project.
 */
async function collectProjectData(project) {
  let reposProcessed = 0;
  const orgErrors = [];

  for (const org of project.organizations) {
    console.log(`[${project.id}] Syncing repos for org: ${org}`);
    try {
      reposProcessed += await syncRepos(org, project.id);
    } catch (err) {
      const status = err.response?.status;
      const message = err.response?.data?.message || err.message;
      console.error(`[${project.id}] Skipping org ${org}: ${message}`);
      orgErrors.push({ org, status, message });
    }
  }

  if (orgErrors.length > 0) {
    console.error(
      `[${project.id}] Skipping commits/PRs/reviews: repo sync failed for ${orgErrors.length} org(s)`
    );
    return {
      project_id: project.id,
      project_name: project.name,
      organizations: project.organizations,
      repos_processed: reposProcessed,
      commits_processed: 0,
      prs_processed: 0,
      reviews_processed: 0,
      org_errors: orgErrors,
      status: 'failed',
    };
  }

  const commits = await syncCommitsForProject(project.id);
  const prs = await syncPRsForProject(project.id);
  const reviews = await syncReviewsForProject(project.id);

  return {
    project_id: project.id,
    project_name: project.name,
    organizations: project.organizations,
    repos_processed: reposProcessed,
    commits_processed: commits.commitsProcessed,
    prs_processed: prs.prsProcessed,
    reviews_processed: reviews.reviewsProcessed,
    org_errors: orgErrors,
    status: 'success',
  };
}

/**
 * Run the full sync pipeline for every configured project.
 */
async function syncAllProjects() {
  const projects = getProjects();
  const results = [];

  for (const project of projects) {
    console.log(`Starting sync for project: ${project.name} (${project.id})`);
    results.push(await collectProjectData(project));
  }

  return results;
}

module.exports = {
  collectProjectData,
  syncAllProjects,
  syncCommitsForProject,
  syncPRsForProject,
  syncReviewsForProject,
};
