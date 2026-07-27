import axios from "axios";
import type { PeriodValue } from "./periods";

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

// Fetch unique users for an organization
export const fetchUsers = async (org: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${org}/users`);
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

// Fetch tracked GitHub organizations
export const fetchOrganizations = async (): Promise<
  Array<{ id: number; slug: string; name: string }>
> => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/organizations`);
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch organizations");
  }
};

// Fetch assignable user job roles
export const fetchUserRoles = async (): Promise<Array<{ id: number; name: string }>> => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/user-roles`);
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch user roles");
  }
};

// Fetch org-wide activity chart data
export const fetchOrgActivity = async (
  orgId: string,
  period: string,
  role: string = "all",
) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${orgId}/activity`, {
      params: { period, role },
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
  role: string = "all",
  search: string = "",
  sortBy?: "prs" | "reviews" | "issues" | null,
  sortOrder: "asc" | "desc" = "desc",
) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${org}/users`, {
      params: {
        period,
        page,
        limit,
        role,
        ...(search ? { search } : {}),
        ...(sortBy ? { sortBy, sortOrder } : {}),
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
  role: string = "all",
  limit: number = 10,
) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/orgs/${org}/leaderboard`,
      {
        params: { period, limit, role },
      },
    );

    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch leaderboard");
  }
};

// Fetch organization summary (commits, PRs, reviews, issues)
export const fetchOrgSummary = async (
  orgId: string,
  period: string,
  role: string = "all",
) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/orgs/${orgId}/summary`, {
      params: { period, role },
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
  period: PeriodValue,
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
