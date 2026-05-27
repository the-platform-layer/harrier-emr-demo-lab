-- Example PR-ready migration for db_partition_hotspot.
-- Review table and column names before use.
--
-- Prefer Spark JDBC partitioning fixes first. Use DB partitioning only when
-- data lifecycle and query patterns justify the schema change.

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_events_partition_key
--   ON demo_events (partition_key);

