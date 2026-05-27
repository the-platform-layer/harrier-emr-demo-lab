"""Placeholder DB partition hotspot scenario job.

This scenario will intentionally use poor JDBC partitioning over a large demo
table so Harrier can correlate Spark task imbalance with read-only PostgreSQL
diagnostics and suggest PR-ready Spark/SQL remediation.
"""

