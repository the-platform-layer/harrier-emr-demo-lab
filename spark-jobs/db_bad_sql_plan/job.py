"""Placeholder DB bad SQL plan scenario job.

This scenario will run a Spark/JDBC query that produces an inefficient or
failed PostgreSQL plan. Harrier should use read-only SQL plan evidence and
metadata to suggest PR-ready SQL/query changes.
"""

