-- Read-only diagnostics for the db_partition_hotspot scenario.
--
-- Intended checks:
-- - identify long-running JDBC reads/writes
-- - inspect approximate row distribution by candidate partition key
-- - inspect table and index metadata
--
-- Scenario implementation will replace table names with demo schema names.

select
  pid,
  state,
  wait_event_type,
  wait_event,
  now() - query_start as query_age,
  left(query, 500) as query_excerpt
from pg_stat_activity
where datname = current_database()
order by query_age desc nulls last;

