-- Backdate user_details.active_from so historical activity before user sync
-- is included when a role is first assigned.
UPDATE user_details ud
SET
  active_from = LEAST(
    ud.active_from,
    COALESCE(
      (SELECT MIN(e.created_at) FROM activity_events e WHERE e.user_id = ud.user_id),
      ud.active_from
    )
  ),
  updated_at = CURRENT_TIMESTAMP
WHERE EXISTS (
  SELECT 1 FROM activity_events e WHERE e.user_id = ud.user_id
);

-- First role assignment rows should cover all prior activity, not only from assignment time.
UPDATE user_details current_ud
SET
  active_from = LEAST(
    current_ud.active_from,
    COALESCE(
      (SELECT MIN(e.created_at) FROM activity_events e WHERE e.user_id = current_ud.user_id),
      current_ud.active_from
    ),
    COALESCE(
      (SELECT MIN(h.active_from) FROM user_details h WHERE h.user_id = current_ud.user_id),
      current_ud.active_from
    )
  ),
  updated_at = CURRENT_TIMESTAMP
WHERE current_ud.role_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM user_details prior_role
    WHERE prior_role.user_id = current_ud.user_id
      AND prior_role.role_id IS NOT NULL
      AND prior_role.id <> current_ud.id
      AND prior_role.active_to IS NOT NULL
      AND prior_role.active_to <= current_ud.active_from
  );
