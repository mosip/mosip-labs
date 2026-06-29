import axios from "axios";

// Production: use relative URLs (nginx proxies /orgs/, /admin/, /projects to backend)
// Development: use direct backend URL
const API_BASE_URL = import.meta.env.PROD
  ? ""
  : (import.meta.env.VITE_API_BASE_URL || "http://localhost:3000");

export interface Project {
  id: string;
  name: string;
}

const DASHBOARD_ORG = "dashboard";

function projectParams(project: string) {
  return project && project !== "all" ? { project } : { project: "all" };
}

export const fetchProjects = async (): Promise<Project[]> => {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects`);
    return response.data.projects || [];
  } catch (error) {
    throw new Error("Failed to fetch projects");
  }
};

export const fetchUsers = async (project: string = "all") => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${DASHBOARD_ORG}/users`, {
      params: { period: "weekly", ...projectParams(project) },
    });
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch users");
  }
};

export const fetchOrgActivity = async (
  period: string,
  project: string = "all",
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/activity`,
      {
        params: { period, ...projectParams(project) },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch org activity");
  }
};

export const fetchOrgUsers = async (
  project: string,
  period: string,
  page: number = 1,
  limit: number = 20,
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/users`,
      {
        params: {
          period,
          page,
          limit,
          ...projectParams(project),
        },
      },
    );

    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch org users");
  }
};

export const fetchLeaderboard = async (
  project: string,
  period: string,
  limit: number = 10,
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/leaderboard`,
      {
        params: { period, limit, ...projectParams(project) },
      },
    );

    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch leaderboard");
  }
};

export const fetchOrgSummary = async (
  period: string,
  project: string = "all",
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/summary`,
      {
        params: { period, ...projectParams(project) },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch organization summary");
  }
};

export const fetchUserDetails = async (
  login: string,
  period: "daily" | "weekly" | "monthly",
  project: string = "all",
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/users/${login}`,
      {
        params: { period, ...projectParams(project) },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch user details");
  }
};

export const downloadExport = async (
  project: string,
  period: string,
  format: "csv" | "json",
) => {
  const response = await axios.get(
    `${API_BASE_URL}/orgs/${DASHBOARD_ORG}/export`,
    {
      params: { period, format, ...projectParams(project) },
      responseType: format === "csv" ? "blob" : "json",
    },
  );

  const blob =
    format === "csv"
      ? new Blob([response.data], { type: "text/csv" })
      : new Blob([JSON.stringify(response.data, null, 2)], {
          type: "application/json",
        });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `github-activity-${project}-${period}.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

// Legacy API helpers (unused by current dashboard)
export const fetchRepositories = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/repositories`);
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch repositories");
  }
};

export const fetchRepository = async (id: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/repository/${id}`);
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch repository");
  }
};

export const fetchActivityData = async (
  repo: string,
  dateRange: string,
  startDate?: string,
  endDate?: string,
  username?: string,
  repos: string[] = [],
  users: string[] = [],
) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/activity`, {
      params: {
        repo,
        dateRange,
        startDate,
        endDate,
        username,
        repos: repos.join(","),
        users: users.join(","),
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch activity data");
  }
};

export const fetchRepositoryStats = async (repositoryId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/stats/${repositoryId}`,
    );
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch repository stats");
  }
};

export const addRepository = async (repoName: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/addRepo`, {
      repoName,
    });
    return response.data;
  } catch (error) {
    throw new Error("Failed to add repository");
  }
};
