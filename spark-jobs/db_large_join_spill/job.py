"""Placeholder DB large join spill scenario job.

This scenario will create an expensive large join path so Harrier can combine
Spark shuffle/spill evidence with read-only PostgreSQL diagnostics and suggest
reviewable SQL/index or query-rewrite changes.
"""

