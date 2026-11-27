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

// GitHub Search allows 30 requests/minute. Space calls so issue sync still
// runs after PR sync has used the same quota.
const SEARCH_MIN_INTERVAL_MS = 2100;
const MAX_RATE_LIMIT_RETRIES = 5;
const MAX_RATE_LIMIT_WAIT_MS = 90 * 1000;

let searchChain = Promise.resolve();
let nextSearchAt = 0;

function isSearchRequest(config) {
  const url = `${config?.baseURL || ''}${config?.url || ''}`;
  return url.includes('/search/');
}

function scheduleSearchSlot() {
  const run = searchChain.then(async () => {
    const wait = Math.max(0, nextSearchAt - Date.now());
    if (wait > 0) await sleep(wait);
    nextSearchAt = Date.now() + SEARCH_MIN_INTERVAL_MS;
  });
  searchChain = run.then(() => {}, () => {});
  return run;
}

function rateLimitWaitMs(headers) {
  const retryAfter = headers['retry-after'];
  if (retryAfter) {
    return Math.min(MAX_RATE_LIMIT_WAIT_MS, Math.max(0, Number(retryAfter) * 1000) + 250);
  }
  const reset = headers['x-ratelimit-reset'];
  if (reset) {
    return Math.min(MAX_RATE_LIMIT_WAIT_MS, Math.max(0, Number(reset) * 1000 - Date.now()) + 1500);
  }
  return 60 * 1000;
}

function isRateLimited(status, headers, data) {
  if (status === HTTP.TOO_MANY_REQUESTS) return true;
  if (status !== HTTP.FORBIDDEN) return false;
  if (String(headers['x-ratelimit-remaining']) === '0') return true;
  const message = typeof data?.message === 'string' ? data.message : '';
  return /rate limit/i.test(message);
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

githubClient.interceptors.request.use(async (config) => {
  if (isSearchRequest(config)) {
    await scheduleSearchSlot();
  }
  return config;
});

githubClient.interceptors.response.use(
  (response) => {
    if (isSearchRequest(response.config || {})) {
      const headers = response.headers || {};
      if (String(headers['x-ratelimit-remaining']) === '0') {
        nextSearchAt = Math.max(nextSearchAt, Date.now() + rateLimitWaitMs(headers));
      }
    }
    return response;
  },
  async (error) => {
    const status = error?.response?.status;
    const headers = error?.response?.headers || {};
    const config = error?.config;

    if (!config) throw error;

    config.__retryCount = config.__retryCount || 0;
    if (config.__retryCount >= MAX_RATE_LIMIT_RETRIES) throw error;
    if (!isRateLimited(status, headers, error.response?.data)) throw error;

    const waitMs = rateLimitWaitMs(headers);
    config.__retryCount += 1;
    nextSearchAt = Math.max(nextSearchAt, Date.now() + waitMs);
    await sleep(waitMs);
    return githubClient.request(config);
  }
);

module.exports = githubClient;
