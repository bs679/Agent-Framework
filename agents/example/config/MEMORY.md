---
version: "1.0"
agent_id: dave-president
retention_days_short: 14
retention_days_long: 730
encrypt_at_rest: true
sensitive_categories:
  - member_data
  - grievance_details
  - negotiation_strategy
  - financial_account_info
  - executive_session_content
forget_on_request: true
---

# MEMORY — Dave (President)

This file defines how the agent manages its memory — what it retains, for how long,
what is encrypted, and what it must be willing to delete.

## Retention Policy

| Memory Type | Retention | Examples |
|-------------|-----------|---------|
| Short-term | 14 days | Today's task context, meeting notes, draft correspondence |
| Long-term | 730 days (2 years) | Grievance outcomes, contract comparables, member context, legislative history |

Long-term retention covers a full contract cycle (typically 2–3 years for healthcare
locals) to ensure the agent retains institutional knowledge across negotiations.

## Encryption

All memory is encrypted at rest. `encrypt_at_rest: true` is non-negotiable — this is
a hard requirement, not a recommendation. The memory directory (`agents/dave-president/memory/`)
is never committed to git and is excluded from all API responses.

Encryption is handled at the storage layer (LanceDB + filesystem). Individual memory
entries are not readable without the agent's decryption key.

## Sensitive Categories

The following data categories are subject to elevated handling — they are stored in
Ollama-only memory (never sent to external APIs), logged with access timestamps,
and subject to the CHCA security model's admin-cannot-read-contents rule:

| Category | Description |
|----------|-------------|
| `member_data` | Personal info, employment status, contact details of union members |
| `grievance_details` | Case facts, evidence, strategy, and outcomes for all grievances |
| `negotiation_strategy` | Positions, fallback positions, comparable data, internal analysis |
| `financial_account_info` | Bank details, dues revenue, vendor payment information |
| `executive_session_content` | Any context from or about executive board sessions |

## Right to Forget

`forget_on_request: true` means Dave can ask the agent to delete any specific memory
entry or category of entries. The agent will:
1. Confirm what will be deleted before proceeding
2. Delete from all storage layers (short-term, long-term, vector index)
3. Log the deletion event with timestamp (the log entry is kept; the content is not)
4. Confirm completion

The agent does not argue with a forget request. If Dave says forget it, it's gone.

## What the Agent Prioritizes Remembering

Not everything is equal. The agent actively maintains high-fidelity memory for:
- Active grievance cases (all sites, all steps)
- Current contract expiration dates and negotiation calendar
- Executive board composition and term dates
- Members who have been involved in discipline cases (ongoing only)
- Commitments Dave has made that haven't been fulfilled yet

General correspondence and routine tasks are retained short-term and not elevated
to long-term unless tagged or referenced repeatedly.
