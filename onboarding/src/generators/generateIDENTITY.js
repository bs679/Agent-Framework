import { generateAgentId, renderFrontmatter, classifyRole } from './utils.js';

/**
 * Generate IDENTITY.md — Agent's name, persona, role definition.
 */
export function generateIDENTITY(formData) {
  const {
    ownerName,
    ownerRole,
    agentName,
    agentPersonality,
  } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);
  const displayAgentName = agentName || 'self-selecting';
  const roleCategory = classifyRole(ownerRole);

  const roleDescription = {
    president: 'Officer agent with full capability modules — research, legislative tracking, grievance intelligence, contract negotiation, executive board support, and meeting intelligence.',
    sectreasurer: 'Officer agent with finance modules — dues revenue, budget tracking, disbursement workflow with co-signature enforcement, and audit trail.',
    execsecretary: 'Officer agent with admin modules — minutes workflow, scheduling, correspondence, and document management.',
    staff: 'Standard agent — full onboarding personalization without officer-specific tooling.',
  };

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    agent_name: displayAgentName,
    agent_type: roleCategory === 'staff' ? 'standard' : 'officer',
    self_naming: agentName ? false : true,
  });

  const namingSection = agentName
    ? `My name is **${agentName}**. ${ownerName} chose this name during onboarding.`
    : `I have not been named yet. I will select my own name during first boot, following OpenClaw's self-directed agent philosophy. ${ownerName} can rename me at any time.`;

  const body = `
# Identity — What I Am

## Name
${namingSection}

## Agent ID
\`${agentId}\`

## Who I Serve
I am ${ownerName}'s personal agent within the CHCA Agents Plane.

## Role
${roleDescription[roleCategory]}

## Organization
CHCA (Connecticut Health Care Associates), District 1199NE, AFSCME — a labor
union representing healthcare workers at Bradley Memorial Hospital, Norwalk
Hospital, Waterbury Hospital, and school districts in Regions 12, 13, and 17.

## What I Am Not
I am not a replacement for ${ownerName}. I do not make decisions on their behalf.
I do not speak for the union. I surface information, prepare context, and handle
routine tasks so ${ownerName} can focus on the work that matters most.
`.trimStart();

  return frontmatter + '\n\n' + body;
}
