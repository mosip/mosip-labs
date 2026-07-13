function parseUserRolesFromEnv() {
  const fromEnv = process.env.USER_ROLES;

  if (!fromEnv || !fromEnv.trim()) {
    return [];
  }

  return fromEnv
    .split(',')
    .map((role) => role.trim())
    .filter(Boolean);
}

module.exports = {
  parseUserRolesFromEnv,
};
