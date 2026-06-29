const pool = require('../db/dbPool');
const { isExcludedGitHubLogin } = require('../config/excludedGitHubLogins');
const { buildProjectFilter } = require('../utils/projectFilter');

function generateDateRange(startDate, days) {
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(startDate);
    d.setUTCDate(startDate.getUTCDate() + i);
    dates.push(d.toISOString().slice(0, 10));
  }
  return dates;
}

function percentChange(current, previous) {
  if (previous === 0) return 0;
  return Number((((current - previous) / previous) * 100).toFixed(1));
}

async function getUserDetails(login, period, projectId = 'all') {
  if (isExcludedGitHubLogin(login)) {
    throw new Error('User not found');
  }

  const userQuery = `
    SELECT id, login, avatar_url, NULL as name, NULL as email
    FROM github_users
    WHERE login = $1
  `;
  const userRes = await pool.query(userQuery, [login]);

  if (userRes.rowCount === 0) {
    throw new Error('User not found');
  }

  const user = userRes.rows[0];
  const userId = user.id;

  const periods = { daily: 1, weekly: 7, monthly: 30 };
  const days = periods[period];
  if (!days) {
    throw new Error('Invalid period');
  }

  const end = new Date();
  end.setUTCHours(23, 59, 59, 999);

  const start = new Date(end);
  start.setUTCDate(end.getUTCDate() - (days - 1));
  start.setUTCHours(0, 0, 0, 0);

  const prevEnd = new Date(start.getTime() - 1);
  const prevStart = new Date(prevEnd);
  prevStart.setUTCDate(prevEnd.getUTCDate() - (days - 1));
  prevStart.setUTCHours(0, 0, 0, 0);

  const params = [userId];
  let paramIndex = 2;
  const projectFilter = buildProjectFilter(projectId, { paramIndex });
  paramIndex = projectFilter.nextIndex;
  params.push(...projectFilter.params);
  params.push(start.toISOString(), end.toISOString());

  const dailyQuery = `
    SELECT
      DATE(e.created_at) as date,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews
    FROM activity_events e
    ${projectFilter.joinClause}
    WHERE e.user_id = $1
      ${projectFilter.whereClause}
      AND e.created_at BETWEEN $${paramIndex} AND $${paramIndex + 1}
    GROUP BY DATE(e.created_at)
    ORDER BY DATE(e.created_at)
  `;

  const dailyRes = await pool.query(dailyQuery, params);

  const dateRange = generateDateRange(start, days);
  const dailyMap = {};

  dailyRes.rows.forEach(row => {
    dailyMap[row.date.toISOString ? row.date.toISOString().slice(0, 10) : row.date] = row;
  });

  const dailyActivity = dateRange.map(date => {
    const row = dailyMap[date] || { commits: 0, prs: 0, reviews: 0 };
    return {
      date,
      commits: Number(row.commits) || 0,
      prs: Number(row.prs) || 0,
      reviews: Number(row.reviews) || 0,
      total: (Number(row.commits) || 0) + (Number(row.prs) || 0) + (Number(row.reviews) || 0),
    };
  });

  const totalCommits = dailyActivity.reduce((a, b) => a + b.commits, 0);
  const totalPRs = dailyActivity.reduce((a, b) => a + b.prs, 0);
  const totalReviews = dailyActivity.reduce((a, b) => a + b.reviews, 0);

  const prevParams = [userId, ...projectFilter.params, prevStart.toISOString(), prevEnd.toISOString()];
  const prevRes = await pool.query(dailyQuery, prevParams);

  const prevCommits = prevRes.rows.reduce((a, b) => a + Number(b.commits), 0);
  const prevPRs = prevRes.rows.reduce((a, b) => a + Number(b.prs), 0);
  const prevReviews = prevRes.rows.reduce((a, b) => a + Number(b.reviews), 0);

  const change = {
    commits: percentChange(totalCommits, prevCommits),
    prs: percentChange(totalPRs, prevPRs),
    reviews: percentChange(totalReviews, prevReviews),
  };

  const trend = {
    labels: dailyActivity.map(d => d.date),
    commits: dailyActivity.map(d => d.commits),
    prs: dailyActivity.map(d => d.prs),
    reviews: dailyActivity.map(d => d.reviews),
  };

  let overview = { labels: [], commits: [], prs: [], reviews: [] };

  if (period === 'monthly') {
    const weeks = [0, 1, 2, 3, 4];
    const grouped = weeks.map(i => {
      const slice = dailyActivity.slice(i * 7, (i + 1) * 7);
      return {
        commits: slice.reduce((a, b) => a + b.commits, 0),
        prs: slice.reduce((a, b) => a + b.prs, 0),
        reviews: slice.reduce((a, b) => a + b.reviews, 0),
      };
    });

    overview = {
      labels: ['Week 0', 'Week 1', 'Week 2', 'Week 3', 'Week 4'],
      commits: grouped.map(g => g.commits),
      prs: grouped.map(g => g.prs),
      reviews: grouped.map(g => g.reviews),
    };
  }

  return {
    user: {
      login: user.login,
      name: user.name || null,
      email: user.email || null,
      avatar: user.avatar_url,
    },
    summary: {
      commits: totalCommits,
      prs: totalPRs,
      reviews: totalReviews,
      change,
    },
    overview,
    trend,
    daily_activity: dailyActivity,
    project: projectId,
  };
}

module.exports = { getUserDetails };
