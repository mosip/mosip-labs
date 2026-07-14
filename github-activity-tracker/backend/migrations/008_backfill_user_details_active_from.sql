-- Backdate user_details.active_from so historical activity before user sync
-- is included when a role is first assigned.
-- Only the earliest assignment row per user is backdated; later role windows
-- keep their original boundaries so history does not overlap.
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
WHERE ud.id = (
    SELECT first_ud.id
    FROM user_details first_ud
    WHERE first_ud.user_id = ud.user_id
    ORDER BY first_ud.active_from ASC, first_ud.id ASC
    LIMIT 1
  )
  AND EXISTS (
    SELECT 1 FROM activity_events e WHERE e.user_id = ud.user_id
  );
