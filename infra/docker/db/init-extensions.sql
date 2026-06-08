CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  RAISE NOTICE 'postgis extension version: %', (SELECT extversion FROM pg_extension WHERE extname = 'postgis');
  RAISE NOTICE 'vector extension version: %', (SELECT extversion FROM pg_extension WHERE extname = 'vector');
END $$;
