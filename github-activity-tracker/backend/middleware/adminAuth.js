/**
 * Bearer-token guard for privileged /admin/* endpoints.
 * Requires ADMIN_API_TOKEN to be configured; rejects requests without a matching token.
 */
const { HTTP, STATUS } = require('../config/errorCodes');

function adminAuth(req, res, next) {
  const configuredToken = process.env.ADMIN_API_TOKEN;

  if (!configuredToken) {
    console.error('ADMIN_API_TOKEN is not configured; rejecting admin request.');
    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Admin API is not configured',
    });
  }

  const authHeader = req.headers.authorization || '';
  const [scheme, token] = authHeader.split(' ');

  if (scheme !== 'Bearer' || !token || token !== configuredToken) {
    return res.status(HTTP.UNAUTHORIZED).json({
      status: STATUS.ERROR,
      message: 'Unauthorized: valid admin bearer token required',
    });
  }

  return next();
}

module.exports = adminAuth;
