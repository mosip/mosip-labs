const dayjs = require('dayjs');
const pool = require('../db/dbPool');
const { isExcludedGitHubLogin } = require('../config/excludedGitHubLogins');
const { userDetailsJoinSql } = require('../utils/userRoleSql');
const { getCustomDateRange } = require('../utils/dateRange');

/* ------------------------------------------------
   Helper: Calculate % change
------------------------------------------------ */
function percentChange(current, previous) {
  if (previous === 0) return 0;
  return Number((((current - previous) / previous) * 100).toFixed(1));
}

/* ------------------------------------------------
   MAIN SERVICE
------------------------------------------------ */
async function getUserDetails(orgId, login, period, role = null, startDate, endDate) {
  if (isExcludedGitHubLogin(login)) {
    throw new Error('User not found');
  }
  /* 1. Get user details */
  const userQuery = `
    SELECT
      u.id,
      u.login,
      u.avatar_url,
      u.name,
      ur.name AS role,
      NULL AS email
    FROM github_users u
    LEFT JOIN user_details ud ON ud.user_id = u.id AND ud.active = true
    LEFT JOIN user_roles ur ON ur.id = ud.role_id
    WHERE u.login = $1
  `;
  const userRes = await pool.query(userQuery, [login]);

  if (userRes.rowCount === 0) {
    throw new Error('User not found');
  }

  const user = userRes.rows[0];
  const userId = user.id;

  /* 2. Determine date ranges */
  let start;
  let end;
  let prevStart;
  let prevEnd;
  let days;

  if (period === 'custom') {
    const range = getCustomDateRange(startDate, endDate);
    start = dayjs(range.start);
    end = dayjs(range.end);
    prevStart = dayjs(range.prevStart);
    prevEnd = dayjs(range.prevEnd);
    days = range.days;
  } else {
    const periods = {
      daily: 1,
      weekly: 7,
      monthly: 30,
      yearly: 365,
    };

    days = periods[period];
    if (!days) {
      throw new Error('Invalid period');
    }

    end = dayjs().endOf('day');
    start = end.subtract(days - 1, 'day').startOf('day');
    prevEnd = start.subtract(1, 'millisecond');
    prevStart = prevEnd.subtract(days - 1, 'day').startOf('day');
  }

  const orgOwner = String(orgId).toLowerCase();

  /* 3. Fetch daily activity for selected range (scoped to org repos) */
  let dailyQuery = `
    SELECT
      DATE(e.created_at) as date,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COALESCE(SUM(e.files_changed) FILTER (WHERE e.event_type = 'pr'), 0) AS pr_files_changed,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews,
      COUNT(*) FILTER (WHERE e.event_type = 'issue') AS issues
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    JOIN repos r ON r.github_repo_id = e.repo_id
  `;

  const dailyParams = [userId, start.toDate(), end.toDate(), orgOwner];

  dailyQuery += userDetailsJoinSql(role ? '$5' : null);

  if (role) {
    dailyParams.push(role);
  }

  dailyQuery += `
    WHERE e.user_id = $1
      AND LOWER(r.owner) = $4
      AND e.created_at BETWEEN $2 AND $3
  `;

  dailyQuery += `
    GROUP BY DATE(e.created_at)
    ORDER BY DATE(e.created_at)
  `;

  const dailyRes = await pool.query(dailyQuery, dailyParams);

  /* 4. Fill missing days (local calendar days, matching SQL DATE buckets) */
  const dateRange = [];
  for (let i = 0; i < days; i++) {
    dateRange.push(start.add(i, 'day').format('YYYY-MM-DD'));
  }

  const dailyMap = {};
  dailyRes.rows.forEach((row) => {
    dailyMap[dayjs(row.date).format('YYYY-MM-DD')] = row;
  });

  const dailyActivity = dateRange.map(date => {
    const row = dailyMap[date] || { commits: 0, prs: 0, pr_files_changed: 0, reviews: 0, issues: 0 };
    return {
      date,
      commits: Number(row.commits) || 0,
      prs: Number(row.prs) || 0,
      pr_files_changed: Number(row.pr_files_changed) || 0,
      reviews: Number(row.reviews) || 0,
      issues: Number(row.issues) || 0,
      total: (Number(row.commits) || 0) + (Number(row.prs) || 0) + (Number(row.reviews) || 0) + (Number(row.issues) || 0),
    };
  });

  /* 5. Summary totals */
  const totalCommits = dailyActivity.reduce((a, b) => a + b.commits, 0);
  const totalPRs = dailyActivity.reduce((a, b) => a + b.prs, 0);
  const totalReviews = dailyActivity.reduce((a, b) => a + b.reviews, 0);
  const totalIssues = dailyActivity.reduce((a, b) => a + b.issues, 0);

  /* 6. Fetch previous period totals */
  const prevParams = [userId, prevStart.toDate(), prevEnd.toDate(), orgOwner];
  if (role) {
    prevParams.push(role);
  }
  const prevRes = await pool.query(dailyQuery, prevParams);

  const prevCommits = prevRes.rows.reduce((a, b) => a + Number(b.commits), 0);
  const prevPRs = prevRes.rows.reduce((a, b) => a + Number(b.prs), 0);
  const prevReviews = prevRes.rows.reduce((a, b) => a + Number(b.reviews), 0);
  const prevIssues = prevRes.rows.reduce((a, b) => a + Number(b.issues), 0);

  /* 7. Compute % changes */
  const change = {
    commits: percentChange(totalCommits, prevCommits),
    prs: percentChange(totalPRs, prevPRs),
    reviews: percentChange(totalReviews, prevReviews),
    issues: percentChange(totalIssues, prevIssues),
  };

  /* 8. Trend chart data (daily) */
  const trend = {
    labels: dailyActivity.map(d => d.date),
    commits: dailyActivity.map(d => d.commits),
    prs: dailyActivity.map(d => d.prs),
    reviews: dailyActivity.map(d => d.reviews),
    issues: dailyActivity.map(d => d.issues),
  };

  /* 9. Overview (weekly buckets for monthly) */
  let overview = { labels: [], commits: [], prs: [], reviews: [], issues: [] };

  if (period === 'monthly') {
    const weeks = [0, 1, 2, 3, 4];
    const grouped = weeks.map(i => {
      const slice = dailyActivity.slice(i * 7, (i + 1) * 7);
      return {
        commits: slice.reduce((a, b) => a + b.commits, 0),
        prs: slice.reduce((a, b) => a + b.prs, 0),
        reviews: slice.reduce((a, b) => a + b.reviews, 0),
        issues: slice.reduce((a, b) => a + b.issues, 0),
      };
    });

    overview = {
      labels: ['Week 0', 'Week 1', 'Week 2', 'Week 3', 'Week 4'],
      commits: grouped.map(g => g.commits),
      prs: grouped.map(g => g.prs),
      reviews: grouped.map(g => g.reviews),
      issues: grouped.map(g => g.issues),
    };
  }

  /* 10. Final response */
  return {
    user: {
      login: user.login,
      name: user.name || null,
      email: user.email || null,
      avatar: user.avatar_url,
      role: user.role || null,
    },
    summary: {
      commits: totalCommits,
      prs: totalPRs,
      reviews: totalReviews,
      issues: totalIssues,
      change,
    },
    overview,
    trend,
    daily_activity: dailyActivity,
  };
}

module.exports = { getUserDetails };