const fs = require('fs');
const path = require('path');

const DEFAULT_PROJECTS_PATH = path.join(__dirname, 'projects.json');

/**
 * Load project definitions from config/projects.json (Option A).
 * GITHUB_PROJECTS env (JSON) overrides the file when set (e.g. Helm/K8s).
 * Format: [{ id, name, organizations: [orgLogin, ...] }, ...]
 */
function loadProjects() {
  if (process.env.GITHUB_PROJECTS) {
    try {
      const parsed = JSON.parse(process.env.GITHUB_PROJECTS);
      return validateProjects(parsed);
    } catch (err) {
      throw new Error(`Invalid GITHUB_PROJECTS JSON: ${err.message}`);
    }
  }

  if (!fs.existsSync(DEFAULT_PROJECTS_PATH)) {
    throw new Error(
      'No project configuration found. Create backend/config/projects.json or set GITHUB_PROJECTS'
    );
  }

  const raw = fs.readFileSync(DEFAULT_PROJECTS_PATH, 'utf8');
  return validateProjects(JSON.parse(raw));
}

function validateProjects(projects) {
  if (!Array.isArray(projects) || projects.length === 0) {
    throw new Error('Project configuration must be a non-empty array');
  }

  const seen = new Set();
  const orgOwners = new Map();
  const validated = projects.map((project, index) => {
    const id = String(project.id || '').trim().toLowerCase();
    const name = String(project.name || '').trim();
    const organizations = Array.isArray(project.organizations)
      ? project.organizations.map((org) => String(org).trim().toLowerCase()).filter(Boolean)
      : [];

    if (!id) {
      throw new Error(`Project at index ${index} is missing id`);
    }
    if (!name) {
      throw new Error(`Project "${id}" is missing name`);
    }
    if (organizations.length === 0) {
      throw new Error(`Project "${id}" must have at least one organization`);
    }
    if (seen.has(id)) {
      throw new Error(`Duplicate project id: ${id}`);
    }

    seen.add(id);
    return { id, name, organizations };
  });

  for (const project of validated) {
    for (const org of project.organizations) {
      const existingProjectId = orgOwners.get(org);
      if (existingProjectId) {
        throw new Error(
          `Organization "${org}" is configured for multiple projects: "${existingProjectId}" and "${project.id}"`
        );
      }
      orgOwners.set(org, project.id);
    }
  }

  return validated;
}

let cachedProjects = null;

function getProjects() {
  if (!cachedProjects) {
    cachedProjects = loadProjects();
  }
  return cachedProjects;
}

function getProjectById(projectId) {
  if (!projectId || projectId === 'all') {
    return null;
  }
  const project = getProjects().find((p) => p.id === projectId.toLowerCase());
  if (!project) {
    throw new Error(`Unknown project: ${projectId}`);
  }
  return project;
}

function getProjectListForApi() {
  return getProjects().map(({ id, name }) => ({ id, name }));
}

module.exports = {
  getProjects,
  getProjectById,
  getProjectListForApi,
  loadProjects,
};
