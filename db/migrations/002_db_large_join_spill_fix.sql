-- Example PR-ready migration for db_large_join_spill.
-- Review table and column names before use.

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_fact_join_key
--   ON demo_fact (join_key);
--
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_dim_join_key
--   ON demo_dim (join_key);

