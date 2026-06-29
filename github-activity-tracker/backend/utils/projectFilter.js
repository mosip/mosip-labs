const { getProjectById } = require('../config/projects');

/**
 * Build SQL fragments for filtering activity by project via repos join.
 * @param {string|null|undefined} projectId - project id or "all"
 * @param {object} options
 * @param {string} options.reposAlias - alias for repos table in query
 * @param {number} options.paramIndex - next $N index for parameterized query
 * @returns {{ joinClause: string, whereClause: string, params: any[], nextIndex: number }}
 */
function buildProjectFilter(projectId, { reposAlias = 'r', paramIndex = 1 } = {}) {
  if (!projectId || projectId === 'all') {
    return {
      joinClause: '',
      whereClause: '',
      params: [],
      nextIndex: paramIndex,
    };
  }

  getProjectById(projectId);

  return {
    joinClause: ` JOIN repos ${reposAlias} ON ${reposAlias}.github_repo_id = e.repo_id `,
    whereClause: ` AND ${reposAlias}.project_id = $${paramIndex} `,
    params: [projectId.toLowerCase()],
    nextIndex: paramIndex + 1,
  };
}

module.exports = {
  buildProjectFilter,
};
