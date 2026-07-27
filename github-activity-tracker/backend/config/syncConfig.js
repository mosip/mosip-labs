/**
 * Sync behaviour configuration (e.g. delays to reduce GitHub rate-limit risk).
 */

/** Delay in ms between processing each repo when syncing commits/PRs/reviews/issues for all repos. */
const DELAY_BETWEEN_REPOS_MS = 300;

/** Default batch size for backfilling missing GitHub user display names per request. */
const NAME_BACKFILL_BATCH_SIZE = 50;

/** Delay in ms between GitHub profile lookups when backfilling user names. */
const NAME_FETCH_DELAY_MS = 120;

/** Maximum batch size allowed for a single user-name backfill request. */
const NAME_BACKFILL_MAX_BATCH_SIZE = 500;

/** Delay in ms before retrying a user whose GitHub name could not be resolved. */
const NAME_FETCH_RETRY_MS = 24 * 60 * 60 * 1000;

/** Interval in ms after which a stored user name is considered stale and should be re-fetched from GitHub. */
const NAME_REFRESH_INTERVAL_MS = 7 * 24 * 60 * 60 * 1000;

module.exports = {
  DELAY_BETWEEN_REPOS_MS,
  NAME_BACKFILL_BATCH_SIZE,
  NAME_FETCH_DELAY_MS,
  NAME_BACKFILL_MAX_BATCH_SIZE,
  NAME_FETCH_RETRY_MS,
  NAME_REFRESH_INTERVAL_MS,
};
