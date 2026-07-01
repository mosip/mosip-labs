export interface Organization {
  id: string;
  label: string;
}

// Org IDs are read from VITE_ORGANIZATIONS (comma-separated) in frontend/.env.
// IDs are kept lowercase to match the `owner` column; labels are uppercased for display.
const organizationsEnv = import.meta.env.VITE_ORGANIZATIONS!;

export const ORGANIZATIONS: Organization[] = organizationsEnv
  .split(",")
  .map((id: string) => id.trim().toLowerCase())
  .filter((id: string) => id.length > 0)
  .map((id: string) => ({ id, label: id.toUpperCase() }));

export const DEFAULT_ORG: string = ORGANIZATIONS[0]!.id;
