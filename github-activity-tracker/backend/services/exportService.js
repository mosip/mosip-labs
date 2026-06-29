const { getOrgSummary } = require('./orgSummaryService');
const { getOrgActivity } = require('./orgActivityService');
const { getLeaderboard } = require('./leaderBoardService');
const { getOrgUsers } = require('./orgUsersService');

async function getExportData(projectId, period) {
  const [summary, activity, leaderboard, users] = await Promise.all([
    getOrgSummary(period, projectId),
    getOrgActivity(period, projectId),
    getLeaderboard(projectId, period, 0),
    getOrgUsers(projectId, period, 1, 0),
  ]);

  return {
    project: projectId,
    period,
    exported_at: new Date().toISOString(),
    summary,
    activity,
    leaderboard: leaderboard.leaderboard,
    users: users.users,
  };
}

function toCsv(data) {
  const lines = [];

  lines.push('Section,Metric,Value');
  lines.push(`Summary,Total Commits,${data.summary.total_commits}`);
  lines.push(`Summary,Total PRs,${data.summary.total_prs}`);
  lines.push(`Summary,Total Reviews,${data.summary.total_reviews}`);
  lines.push(`Summary,Total Activity,${data.summary.total_activity}`);
  lines.push('');

  lines.push('Leaderboard,Rank,Login,Commits,PRs,Reviews,Score');
  data.leaderboard.forEach((row) => {
    lines.push(
      `Leaderboard,${row.rank},${row.login},${row.commits},${row.prs},${row.reviews},${row.score}`
    );
  });
  lines.push('');

  lines.push('Users,Login,Commits,PRs,Reviews,Total Activity');
  data.users.forEach((row) => {
    lines.push(
      `Users,${row.login},${row.commits},${row.prs},${row.reviews},${row.total_activity}`
    );
  });
  lines.push('');

  lines.push('Activity,Date,Commits,PRs,Reviews,Total');
  data.activity.labels.forEach((label, i) => {
    lines.push(
      `Activity,${label},${data.activity.commits[i]},${data.activity.prs[i]},${data.activity.reviews[i]},${data.activity.total[i]}`
    );
  });

  return lines.join('\n');
}

module.exports = {
  getExportData,
  toCsv,
};
