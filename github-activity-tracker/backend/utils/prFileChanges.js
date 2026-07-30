function parsePullNumberFromUrl(htmlUrl) {
  if (!htmlUrl) return null;
  const match = String(htmlUrl).match(/\/pull\/(\d+)(?:[/?#]|$)/);
  if (!match) return null;
  const prNumber = Number.parseInt(match[1], 10);
  return Number.isFinite(prNumber) ? prNumber : null;
}

async function fetchPRChangedFiles(githubClient, owner, name, prNumber) {
  try {
    const response = await githubClient.get(`/repos/${owner}/${name}/pulls/${prNumber}`);
    const changedFiles = Number(response.data?.changed_files);
    return Number.isFinite(changedFiles) ? changedFiles : null;
  } catch (err) {
    console.error(`Error fetching PR #${prNumber} file changes:`, err.message);
    return null;
  }
}

module.exports = {
  parsePullNumberFromUrl,
  fetchPRChangedFiles,
};
