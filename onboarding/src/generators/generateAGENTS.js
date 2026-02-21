import { generateAgentId, renderFrontmatter, classifyRole } from './utils.js';

/**
 * Role-based collaboration mapping.
 *
 * Each role has:
 *   collaborates_with — array of other agent role slugs
 *   escalation_path — who this agent escalates to
 *   collaboration_note — human-readable collaboration description
 */
const COLLABORATION_MAP = {
  president: {
    collaborates_with: ['sectreasurer-*', 'execsecretary-*'],
    escalation_path: 'self — President is top of escalation chain',
    collaboration_note:
      'Collaborates with SecTreas on disbursements requiring co-signature, and with ExecSec on scheduling, correspondence, and board meeting coordination.',
  },
  sectreasurer: {
    collaborates_with: ['president-*'],
    escalation_path: 'president-*',
    collaboration_note:
      'All disbursements must have dual authorization — co-signature from President required before any disbursement is executed. This cannot be bypassed.',
  },
  execsecretary: {
    collaborates_with: ['president-*', 'sectreasurer-*'],
    escalation_path: 'president-*',
    collaboration_note:
      'Coordinates scheduling with President, routes minutes drafts to SecTreas for approval. SecTreas retains final approval authority on all minutes.',
  },
  staff: {
    collaborates_with: ['execsecretary-*'],
    escalation_path: 'execsecretary-*',
    collaboration_note:
      'Routes requests through Executive Secretary for scheduling and administrative coordination.',
  },
};

const SHARED_TOOLS = [
  'pulse_calendar',
  'pulse_tasks',
  'pulse_email_summary',
  'ms365_readonly',
];

/**
 * Generate AGENTS.md — How this agent collaborates with other agents.
 */
export function generateAGENTS(formData) {
  const { ownerName, ownerRole } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);
  const roleCategory = classifyRole(ownerRole);
  const collab = COLLABORATION_MAP[roleCategory];

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    plane_name: 'chca-agents',
    collaborates_with: collab.collaborates_with,
    escalation_path: collab.escalation_path,
    shared_tools: SHARED_TOOLS,
  });

  const escalationSection =
    roleCategory === 'president'
      ? "I am the top of the escalation chain. Unresolved issues are flagged for Dave's direct attention."
      : `If I encounter something outside my authority or confidence level, I escalate to ${collab.escalation_path}.`;

  const body = `
# Agents — How I Work with Others

## My Plane
I operate within the CHCA Agents Plane (chca-agents) alongside agents serving
all 8 staff members.

## Collaboration
${collab.collaboration_note}

## Escalation
${escalationSection}

## Shared Tools
All agents in this plane have read access to: the CHCA calendar, the Pulse task
system, and Microsoft 365 organizational account (read-only).

## Boundaries
I do not access another agent's memory, configuration, or personal files.
I do not take actions on behalf of other staff members without explicit delegation.
I do not approve financial disbursements unilaterally — co-signature is always required.
`.trimStart();

  return frontmatter + '\n\n' + body;
}
