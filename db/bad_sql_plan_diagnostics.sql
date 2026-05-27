-- Read-only diagnostics for the db_bad_sql_plan scenario.
--
-- Intended checks:
-- - capture active SQL text and query age
-- - inspect table and index metadata
-- - run EXPLAIN manually for the scenario query during validation
--
-- Do not run EXPLAIN ANALYZE in the default demo diagnostics unless the query
-- is known to be safe and bounded.

select
  pid,
  state,
  wait_event_type,
  wait_event,
  now() - query_start as query_age,
  left(query, 1000) as query_excerpt
from pg_stat_activity
where datname = current_database()
order by query_age desc nulls last;

select
  schemaname,
  tablename,
  indexname,
  indexdef
from pg_indexes
where schemaname not in ('pg_catalog', 'information_schema')
order by schemaname, tablename, indexname;

-- Example validation command for scenario implementation:
-- EXPLAIN (FORMAT JSON)
-- SELECT ...

