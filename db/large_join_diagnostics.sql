-- Read-only diagnostics for the db_large_join_spill scenario.
--
-- Intended checks:
-- - inspect active join queries
-- - capture EXPLAIN plans manually during scenario validation
-- - review index coverage for join/filter columns

select
  schemaname,
  tablename,
  indexname,
  indexdef
from pg_indexes
where schemaname not in ('pg_catalog', 'information_schema')
order by schemaname, tablename, indexname;

