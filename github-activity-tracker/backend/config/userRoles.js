const USER_ROLES = [
  'Developer',
  'Tech Lead',
  'Architect',
  'Product Owner',
  'Leadership',
  'QA Engineer',
  'DevOps Engineer',
];

function isValidUserRole(role) {
  return USER_ROLES.includes(role);
}

module.exports = {
  USER_ROLES,
  isValidUserRole,
};
