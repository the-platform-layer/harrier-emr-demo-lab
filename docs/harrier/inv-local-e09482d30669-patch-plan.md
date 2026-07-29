# Harrier Patch Plan inv-local-e09482d30669

Harrier generated this patch plan from recommendation metadata. Source files are not modified unless a future patch hint includes a machine-applicable, allowlisted edit.

## finding-001-rec-001: Increase executor memory and memory overhead

- Type: `SPARK_CONFIG`
- Risk: `low`
- Suggested file: `conf/spark-defaults.conf`

Suggested changes:

- spark.executor.memory=4g  # increase from current value
- spark.executor.memoryOverhead=1024  # minimum 10% of executor memory
