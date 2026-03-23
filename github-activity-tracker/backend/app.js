/**
 * GitHub Activity Tracker – Backend API
 *
 * Express server that exposes admin sync endpoints to pull repository, commit,
 * PR, and review data from GitHub into PostgreSQL. Run migrations first (npm run migrate).
 */
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const repoSyncRoute = require('./routes/repoSyncRoute');
const commitSyncRoute = require('./routes/commitSyncRoute');
const prSyncRoute = require('./routes/prSyncRoute');
const reviewSyncRoute = require('./routes/reviewSyncRoute');
const leaderboardRoute = require('./routes/leaderBoardRoute');
const orgActivityRoute = require('./routes/orgActivityRoute');
const orgSummaryRoute = require('./routes/orgSummaryRoute');
const orgUsersRoute = require('./routes/orgUsersRoute');
const userDetailsRoute = require('./routes/userDetailsRoute');

const app = express();
const PORT = process.env.PORT || 3000;

// Allow frontend (or other origins) to call this API
app.use(cors());
// app.use(cors({ origin: (process.env.ALLOWED_ORIGINS || '').split(',').filter(Boolean) }));
app.use(express.json());

// Health / API info – list available sync endpoints
app.get('/', (req, res) => {
  res.json({
    message: 'GitHub Activity Tracker API',
    endpoints: {
      'POST /admin/sync/repos': 'Sync repositories for an organization',
      'POST /admin/sync/commits': 'Sync commits for all repositories in DB',
      'POST /admin/sync/prs': 'Sync PRs for all repositories in DB',
      'POST /admin/sync/reviews': 'Sync PR reviews for all repositories in DB',
    },
  });
});

// Mount sync route handlers (POST /admin/sync/repos, /commits, /prs, /reviews)
app.use(repoSyncRoute);
app.use(commitSyncRoute);
app.use(prSyncRoute);
app.use(reviewSyncRoute);
app.use(orgUsersRoute);
app.use(orgSummaryRoute);
app.use(userDetailsRoute);
app.use(orgActivityRoute);
app.use(leaderboardRoute);

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
