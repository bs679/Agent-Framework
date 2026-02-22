---
version: "1.0"
agent_id: president-dave
retention_days_short: 30
retention_days_long: 365
encrypt_at_rest: true
sensitive_categories:
  - member_data
  - grievance_details
  - negotiation_strategy
  - financial_account_info
  - executive_session_content
forget_on_request: true
never_forget:
  - contract_deadlines
  - grievance_outcomes
auto_forget:
  - daily_scheduling_details
---

# Memory

Retains important union information for one year. Sensitive categories are encrypted at rest.
