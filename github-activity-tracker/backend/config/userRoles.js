const {
  getAllUserRoles,
  getUserRoleNames,
  isValidUserRole,
} = require('../services/userRolesService');

/**
 * Validate an optional role query value and normalize it into a filter.
 * Returns { error } when the role is invalid, otherwise { roleFilter }
 * where roleFilter is null for missing/"all" roles.
 */
async function resolveRoleFilter(role) {
  if (role && role !== 'all' && !(await isValidUserRole(role))) {
    return { error: 'Invalid role value' };
  }

  return { roleFilter: role && role !== 'all' ? role : null };
}

module.exports = {
  getAllUserRoles,
  getUserRoleNames,
  isValidUserRole,
  resolveRoleFilter,
};