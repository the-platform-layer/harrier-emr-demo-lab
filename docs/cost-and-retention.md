# Cost And Retention

Required controls:

- EMR auto-termination policy
- Smallest practical instance sizes
- RDS disabled by default until DB scenarios are enabled
- S3 lifecycle expiration
- CloudWatch log retention
- Optional AWS Budget or cost alarm

Default retention targets:

- Raw sample data: 7 days
- Processed sample output: 7 days
- EMR/Spark logs: 14 days
- Validation reports: 30 days
- Demo secrets: delete on destroy

