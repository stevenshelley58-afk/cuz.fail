UPDATE target_manifest SET status = 'metadata_only', notes = 'No resolvable URL - cited but unfetchable' WHERE status = 'pending' AND canonical_url = '';
