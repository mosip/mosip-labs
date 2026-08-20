import axios from "axios";

// Production: use relative URLs (nginx proxies /orgs/, /admin/ to backend - no CORS)
// Development: use direct backend URL
const API_BASE_URL = import.meta.env.PROD
  ? ""
  : (import.meta.env.VITE_API_BASE_URL || "http://localhost:3000");

// Fetch list of repositories
export const fetchRepositories = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/repositories`);
    return response.data; // Expect [{ id: string, name: string, created_at: string }, ...]
  } catch (error) {
    throw new Error("Failed to fetch repositories");
  }
};

// Fetch a single repository by ID
export const fetchRepository = async (id: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/repository/${id}`);
    return response.data; // Expect { id: string, name: string, created_at: string }
  } catch (error) {
    throw new Error("Failed to fetch repository");
  }
};

// Fetch unique users
export const fetchUsers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/mosip/users`);
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch users");
  }
};
// Fetch activity data
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
    return response.data; // Expect [{ id: string, repo_name: string, type: string, author: string, created_at: string, ... }, ...]
  } catch (error) {
    throw new Error("Failed to fetch activity data");
  }
};

// Fetch repository stats
export const fetchRepositoryStats = async (repositoryId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/stats/${repositoryId}`,
    );
    return response.data; // Expect { commits: number, issues: number, pullRequests: number, reviews: number }
  } catch (error) {
    throw new Error("Failed to fetch repository stats");
  }
};

// Fetch org-wide activity chart data
export const fetchOrgActivity = async (orgId: string, period: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${orgId}/activity`, {
      params: { period },
    });
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch org activity");
  }
};

// Fetch org users (with period support)
export const fetchOrgUsers = async (
  org: string,
  period: string,
  page: number = 1,
  limit: number = 20,
) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${org}/users`, {
      params: {
        period,
        page,
        limit,
      },
    });

    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch org users");
  }
};

// Fetch LeaderBoard user details
export const fetchLeaderboard = async (
  org: string,
  period: string,
  limit: number = 10,
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${org}/leaderboard`,
      {
        params: { period, limit },
      },
    );

    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch leaderboard");
  }
};

// Fetch organization summary (commits, PRs, reviews)
export const fetchOrgSummary = async (orgId: string, period: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${orgId}/summary`, {
      params: { period },
    });
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch organization summary");
  }
};

// Fetch single user profile details
export const fetchUserDetails = async (
  orgId: string,
  login: string,
  period: "daily" | "weekly" | "monthly",
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${orgId}/users/${login}`,
      {
        params: { period },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch user details");
  }
};

// Add a new repository
export const addRepository = async (repoName: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/addRepo`, {
      repoName,
    });
    return response.data; // Expect { success: boolean, message?: string }
  } catch (error) {
    throw new Error("Failed to add repository");
  }
};