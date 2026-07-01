export interface Organization {
  id: string;
  label: string;
}

// Org IDs are read from VITE_ORGANIZATIONS (comma-separated) and kept lowercase
// to match the `owner` column in the database. Labels are derived by uppercasing.
export const ORGANIZATIONS: Organization[] = (
  import.meta.env.VITE_ORGANIZATIONS ?? "mosip,inji"
)
  .split(",")
  .map((id: string) => id.trim().toLowerCase())
  .filter((id: string) => id.length > 0)
  .map((id: string) => ({ id, label: id.toUpperCase() }));

export const DEFAULT_ORG: string = ORGANIZATIONS[0]?.id ?? "mosip";
