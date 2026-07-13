/**
 * Routes:
 *   GET  /admin/users/:login/role  – fetch role for a GitHub user
 *   POST /admin/users/role         – assign or change role for a GitHub user
 */
const express = require('express');
const { getUserRole, setUserRole } = require('../services/userRoleService');
const { getUserRoleNames } = require('../config/userRoles');
const { getOrganizationNames } = require('../config/organizations');
const { HTTP, STATUS } = require('../config/errorCodes');

const router = express.Router();

router.get('/admin/users/:login/role', async (req, res) => {
  try {
    const { login } = req.params;

    if (!login) {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'login is required',
      });
    }

    const user = await getUserRole(login);

    if (!user) {
      return res.status(HTTP.NOT_FOUND).json({
        status: STATUS.ERROR,
        message: 'User not found',
      });
    }

    return res.json({
      status: STATUS.SUCCESS,
      user,
    });
  } catch (error) {
    console.error('Error fetching user role:', error);

    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to fetch user role',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
    });
  }
});

router.post('/admin/users/role', async (req, res) => {
  try {
    const { login, role, organization } = req.body || {};

    if (!login) {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'login is required in request body',
      });
    }

    if (!role) {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'role is required in request body',
        allowed_roles: await getUserRoleNames(),
      });
    }

    if (!organization) {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'organization is required in request body',
        allowed_organizations: await getOrganizationNames(),
      });
    }

    const user = await setUserRole({ login, role, organization });

    if (!user) {
      return res.status(HTTP.NOT_FOUND).json({
        status: STATUS.ERROR,
        message: 'User not found',
      });
    }

    return res.json({
      status: STATUS.SUCCESS,
      message: 'Role assigned successfully',
      user,
    });
  } catch (error) {
    if (error.message === 'Invalid role value') {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'Invalid role value',
        allowed_roles: await getUserRoleNames(),
      });
    }

    if (error.message === 'Invalid organization value') {
      return res.status(HTTP.BAD_REQUEST).json({
        status: STATUS.ERROR,
        message: 'Invalid organization value',
        allowed_organizations: await getOrganizationNames(),
      });
    }

    console.error('Error assigning user role:', error);

    return res.status(HTTP.INTERNAL_SERVER_ERROR).json({
      status: STATUS.ERROR,
      message: 'Failed to assign user role',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined,
    });
  }
});

module.exports = router;
