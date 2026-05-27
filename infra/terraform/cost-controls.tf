locals {
  budget_setup_note = format(
    "Create an AWS Budget or billing alarm for Project=harrier-demo at approximately $%.0f/month. See docs/cost-and-retention.md.",
    var.monthly_budget_limit_usd,
  )
}
