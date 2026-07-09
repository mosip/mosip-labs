/**
 * Route: POST /admin/sync/user-names
 * Backfills GitHub profile display names for users missing name in github_users.
 */
const express = require('express');
const { backfillMissingUserNames } = require('../services/githubUserService');
const { HTTP, STATUS } = require('../config/errorCodes');

const router = express.Router();

router.post('/admin/sync/user-names', async (req, res) => {
  try {
    const result = await backfillMissingUserNames({
      limit: req.body?.limit,
    });

    return res.json({
      status: STATUS.SUCCESS,
      ...result,
    });
  } catch (error) {
    if (error.statusCode === HTTP.BAD_REQUEST) {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: error.message,
      });
    }

    console.error('Error backfilling GitHub user names:', error);

    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to backfill GitHub user names',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
    });
  }
});

module.exports = router;
