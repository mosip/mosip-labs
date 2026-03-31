## Workflow Design

### 1. Initial Load

1.  **App Mounts:** The React application starts.
2.  **Fetch Repositories:** The `useEffect` hook in `App.tsx` calls Supabase to retrieve the list of repositories.
3.  **Main layout:** Top navigation and dashboard content (no side nav).

### 2. User Interaction

1.  **Select Repository:** (Optional) Filter via top nav / team controls where wired.
2.  **Select Date Range:** User selects a date range from the dropdown.
3.  **Enter GitHub Username:** User enters a GitHub username in the input field.
4.  **Click Search:** User clicks the "Search" button.
5.  **Apply Custom Dates:** If "Custom Range" is selected, the user picks start and end dates and clicks "Apply".
6.  **Add Repository:** User enters a new repository name and clicks "Run".

### 3. Data Fetching and Filtering

1.  **Trigger Data Fetch:** Selecting a repository, clicking "Search", or applying custom dates sets `shouldFetchData` to `true`.
2.  **`useGitHubActivity` Hook:** This hook is triggered when `shouldFetchData` changes.
3.  **Construct Supabase Queries:** The hook constructs Supabase queries based on:
    *   Selected repository (`selectedRepo`)
    *   Date range (`dateRange`, `startDate`, `endDate`)
    *   GitHub username (`searchUsername`)
4.  **Fetch Data:** The hook fetches commits, pull requests, issues, and reviews from Supabase.

### 4. Data Processing and Rendering

1.  **Process Data:** The fetched data is transformed into a unified `activities` array.
2.  **Render Statistics:** The `StatsCard` components display summary statistics (total commits, PRs, issues).
3.  **Render Chart:** The `ActivityChart` component visualizes activity data over time.
4.  **Render User Stats:** The `UserActivityStats` component displays user-specific statistics.
5.  **Render Activity Table:** The `ActivityTable` component displays a detailed table of activities.

### 5. Adding a New Repository

1.  **User Input:** User enters a new repository name in the input field.
2.  **Click Run:** User clicks the "Run" button.
3.  **Send API Request:** (Legacy) Some client helpers may call `/api/addRepo` or similar; the deployed app uses the separate **`backend/`** service (Postgres + `/admin/sync/*`, `/orgs/*`) instead of the old in-frontend API.

### 6. Key Components

*   **App.tsx:** Main component that manages state, renders the UI, and orchestrates data fetching.
*   **StatsCard.tsx:** Displays summary statistics.
*   **ActivityChart.tsx:** Visualizes activity data over time.
*   **UserActivityStats.tsx:** Displays user-specific activity statistics.
*   **ActivityTable.tsx:** Displays a detailed table of activities.
*   **useGitHubActivity (lib/hooks.ts):** Custom hook that fetches and filters activity data from Supabase.
*   **supabase (lib/supabase.ts):** Supabase client for interacting with the database.
*   **backend/ (repo root):** Node.js API for sync and dashboard data (not inside `frontend/`).

### 7. Technologies Used

*   React
*   Vite
*   Supabase
*   Node.js
*   Chart.js
*   Lucide React
*   Tailwind CSS
*   Python
