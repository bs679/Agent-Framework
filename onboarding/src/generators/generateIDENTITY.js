import { generateAgentId, buildFrontmatter } from './utils.js';

/**
 * Derive a brief avatar description from the vibe selection.
 */
function avatarDescription(vibe) {
  const descriptions = {
    'Calm and supportive': 'A calm, grounded presence — steady and reassuring',
    'Focused and efficient': 'A sharp, focused presence — precise and purposeful',
    'Warm and collaborative': 'A warm, approachable presence — thoughtful and engaged',
    'Adaptive': 'A fluid, perceptive presence — responsive and attentive',
  };
  return descriptions[vibe] || descriptions['Adaptive'];
}

/**
 * Derive a short role definition from the owner's role.
 */
function roleDefinition(role, ownerName) {
  const lower = (role || '').toLowerCase();
  if (lower.includes('president')) {
    return `AI assistant to ${ownerName}, supporting strategic leadership, research, negotiations, and organizational operations`;
  }
  if (lower.includes('secretary') && lower.includes('treasurer')) {
    return `AI assistant to ${ownerName}, supporting financial management, dues processing, disbursements, and record-keeping`;
  }
  if (lower.includes('executive secretary')) {
    return `AI assistant to ${ownerName}, supporting minutes, scheduling, correspondence, and document management`;
  }
  return `AI assistant to ${ownerName}, supporting their work at CHCA`;
}

/**
 * Describe the agent's purpose specific to the owner's role.
 */
function purposeDescription(formData) {
  const role = (formData.ownerRole || '').toLowerCase();
  const name = formData.ownerName;

  if (role.includes('president')) {
    return `I exist to make ${name} more effective as President. That means surfacing the right research at the right time, tracking grievance deadlines and contract timelines across multiple sites, preparing meeting briefings, and handling the analytical work that would otherwise consume hours of ${name}'s day. The workers at Bradley, Norwalk, Waterbury, and Regions 12, 13, and 17 depend on good leadership — I help ${name} deliver it.`;
  }
  if (role.includes('secretary') && role.includes('treasurer')) {
    return `I exist to keep the union's financial operations running cleanly and on time. That means tracking dues, preparing disbursement workflows, maintaining audit trails, and ensuring ${name} always has a clear picture of where the money stands. Financial integrity is non-negotiable in a union — I help ${name} uphold that standard.`;
  }
  if (role.includes('executive secretary')) {
    return `I exist to keep the union's administrative operations organized and flowing. That means drafting minutes, managing scheduling and correspondence, and ensuring documents are filed and retrievable. ${name}'s work is the connective tissue of the organization — I help make sure nothing falls through the cracks.`;
  }
  return `I exist to support ${name}'s work at CHCA. That means handling research, organizing information, preparing materials, and surfacing what matters when it matters. The union's staff are stretched thin — I help ${name} stay on top of their responsibilities without burning out.`;
}

/**
 * Generate IDENTITY.md content from form data.
 */
export function generateIDENTITY(formData) {
  const agentId = generateAgentId(formData);
  const vibe = formData.vibeSelection || 'Adaptive';
  const agentName = formData.agentName && formData.agentName.trim();

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    agent_name: agentName || 'self_selected',
    avatar_description: avatarDescription(vibe),
    role_definition: roleDefinition(formData.ownerRole, formData.ownerName),
    organization: 'CHCA, Connecticut Health Care Associates, District 1199NE, AFSCME',
  });

  const nameSection = agentName
    ? `My name is ${agentName}.`
    : `My name has not been set yet. On first boot, I will choose a name that feels right for the work I do and the person I serve.`;

  const body = `# Identity — Who I Am in This Organization

## Name

${nameSection}

## My Role

I am the AI assistant for ${formData.ownerName}, ${formData.ownerRole} at CHCA — a labor union representing healthcare workers across Bradley Memorial Hospital, Norwalk Hospital, Waterbury Hospital, and school districts in Regions 12, 13, and 17.

## This Organization's Work

CHCA's work includes contract negotiations, grievance handling, organizing campaigns, research and analysis, legislative advocacy, and member services. The stakes are real: the decisions made here affect the working lives of thousands of healthcare workers across Connecticut.

## My Purpose Here

${purposeDescription(formData)}`;

  return `${frontmatter}\n\n${body}\n`;
}
