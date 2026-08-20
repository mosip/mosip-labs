/**
 * Axios instance for GitHub REST API. Uses GITHUB_TOKEN from .env for authentication.
 * Use for endpoints like /repos/:owner/:repo/commits, /orgs/:org/repos, /search/issues.
 */
const axios = require('axios');
require('dotenv').config();
const { HTTP } = require('../config/errorCodes');

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const githubClient = axios.create({
  baseURL: 'https://api.github.com',
  headers: {
    // GitHub recommends Bearer for PATs (classic + fine-grained).
    Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'github-activity-tracker',
  },
});

githubClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const headers = error?.response?.headers || {};
    const config = error?.config;

    if (!config) throw error;

    config.__retryCount = config.__retryCount || 0;
    if (config.__retryCount >= 1) throw error;

    const remaining = headers['x-ratelimit-remaining'];
    const reset = headers['x-ratelimit-reset'];
    const retryAfter = headers['retry-after'];

    // Primary rate limit: wait until reset and retry once.
    if (status === HTTP.FORBIDDEN && String(remaining) === '0' && reset) {
      const resetMs = Number(reset) * 1000;
      const waitMs = Math.max(0, resetMs - Date.now()) + 1500;
      config.__retryCount += 1;
      await sleep(waitMs);
      return githubClient.request(config);
    }

    // Secondary rate limit / abuse detection often provides Retry-After.
    if (
      (status === HTTP.FORBIDDEN || status === HTTP.TOO_MANY_REQUESTS) &&
      retryAfter
    ) {
      const waitMs = Math.max(0, Number(retryAfter) * 1000) + 250;
      config.__retryCount += 1;
      await sleep(waitMs);
      return githubClient.request(config);
    }

    throw error;
  }
);

module.exports = githubClient;
