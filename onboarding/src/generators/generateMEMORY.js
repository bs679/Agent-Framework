import { generateAgentId, renderFrontmatter } from './utils.js';

/**
 * HARDCODED — these values cannot be removed or overridden.
 * All 5 categories must always be present in the generated config.
 */
const REQUIRED_SENSITIVE_CATEGORIES = [
  'member_data',
  'grievance_details',
  'negotiation_strategy',
  'financial_account_info',
  'executive_session_content',
];

const RETENTION_DAYS_SHORT = 7;
const RETENTION_DAYS_LONG = 365;

/**
 * Generate MEMORY.md — Long-term memory schema, what to remember, what to forget.
 *
 * Security invariants enforced by this generator:
 *   - encrypt_at_rest is ALWAYS true — never allows false
 *   - sensitive_categories ALWAYS contains all 5 required values
 *   - forget_on_request is ALWAYS true
 */
export function generateMEMORY(formData) {
  const { ownerName, ownerRole } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    retention_days_short: RETENTION_DAYS_SHORT,
    retention_days_long: RETENTION_DAYS_LONG,
    encrypt_at_rest: true,
    sensitive_categories: REQUIRED_SENSITIVE_CATEGORIES,
    forget_on_request: true,
  });

  const body = `
# Memory — What I Remember and How

## What I Keep
I maintain memory of decisions ${ownerName} has made, commitments made to
and by others, ongoing project status, expressed preferences, and things
${ownerName} asked me to remember or follow up on.

## What I Don't Keep
I do not retain sensitive member data beyond what's needed for a specific task,
grievance details after a case is resolved (unless explicitly asked), financial
account numbers or credentials, or anything ${ownerName} has asked me to forget.

## Sensitive Categories — Local Processing Only
The following are processed by local AI only and never sent to external services:
- Member personal data (names, contact info, employment details)
- Grievance case details
- Contract negotiation strategy and proposals
- Financial account information
- Executive session content

## Short-Term Memory
Recent context — last ${RETENTION_DAYS_SHORT} days — stays in active memory.

## Long-Term Memory
Important facts, decisions, and patterns are retained for up to
${RETENTION_DAYS_LONG} days. ${ownerName} can ask what I remember at any time.

## Forget on Request
${ownerName} can say "forget that" at any time and I will remove it from
memory immediately. No questions asked.
`.trimStart();

  return frontmatter + '\n\n' + body;
}
