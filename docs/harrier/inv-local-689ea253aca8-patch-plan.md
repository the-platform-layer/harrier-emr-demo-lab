# Harrier Patch Plan inv-local-689ea253aca8

Harrier generated this patch plan from recommendation metadata. Some source files may also be modified when a recommendation maps to a machine-applicable, allowlisted edit.

## finding-001-rec-001: Increase executor memory and memory overhead

- Type: `SPARK_CONFIG`
- Risk: `low`
- Suggested file: `conf/spark-defaults.conf`

Suggested changes:

- spark.executor.memory=4g  # increase from current value
- spark.executor.memoryOverhead=1024  # minimum 10% of executor memory
