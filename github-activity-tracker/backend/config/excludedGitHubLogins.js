/**
 * GitHub logins to exclude from sync processing (case-insensitive).
 * Keep this list centralized so services don't hard-code values.
 */
const EXCLUDED_GITHUB_LOGINS = ['dependabot[bot]', 'coderabbitai'];

function isExcludedGitHubLogin(login) {
  if (!login) return false;
  const normalized = String(login).toLowerCase();
  return EXCLUDED_GITHUB_LOGINS.includes(normalized);
}

module.exports = {
  EXCLUDED_GITHUB_LOGINS,
  isExcludedGitHubLogin,
};

