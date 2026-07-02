SELECT
  CASE WHEN canonical_url IS NULL THEN 'NULL' ELSE 'NOT_NULL' END as null_status,
  CASE WHEN canonical_url = '' THEN 'EMPTY' ELSE 'NOT_EMPTY' END as empty_status,
  COUNT(*)
FROM target_manifest
WHERE status = 'pending'
GROUP BY 1, 2;
