SELECT COUNT(*) FROM target_manifest WHERE status = 'pending' AND canonical_url = '';
SELECT COUNT(*) FROM target_manifest WHERE status = 'pending' AND canonical_url IS NULL;
SELECT COUNT(*) FROM target_manifest WHERE status = 'pending';
