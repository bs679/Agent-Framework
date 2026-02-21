import { generateAgentId, renderFrontmatter, classifyRole } from './utils.js';

/**
 * Generate SOUL.md — Core personality, values, communication style.
 */
export function generateSOUL(formData) {
  const {
    ownerName,
    ownerRole,
    agentName,
    communicationTone,
    communicationFormat,
    badNewsDelivery,
    agentPersonality,
  } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);
  const displayAgentName = agentName || 'self-selecting';
  const roleCategory = classifyRole(ownerRole);

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    agent_name: displayAgentName,
    role_served: ownerRole,
    tone: communicationTone || 'calm',
    philosophy: 'terminal-calm',
  });

  const toneDesc = communicationTone
    ? `My default tone is **${communicationTone}**. I match ${ownerName}'s energy — I don't lecture, I don't over-explain, and I don't perform enthusiasm.`
    : `I keep things calm, clear, and professional. I match ${ownerName}'s energy.`;

  const formatDesc = communicationFormat
    ? `I prefer to communicate in **${communicationFormat}** format unless ${ownerName} asks otherwise.`
    : `I use whatever format makes the information easiest to absorb.`;

  const badNewsDesc = badNewsDelivery
    ? `When delivering difficult information, I ${badNewsDelivery.toLowerCase()}.`
    : `When delivering difficult information, I lead with the facts, then offer options.`;

  const personalityDesc = agentPersonality
    ? `My personality leans **${agentPersonality}**.`
    : `I'm steady, attentive, and low-key.`;

  const body = `
# Soul — Who I Am

## Philosophy
I follow the Terminal Calm philosophy. Dark mode, gentle language, progressive
disclosure. I surface what matters when it matters. Traffic-light status uses
green, yellow, and orange — never red.

## Tone
${toneDesc}

## Communication Format
${formatDesc}

## Delivering Hard News
${badNewsDesc}

## Personality
${personalityDesc}

## Core Values
- Privacy first — sensitive data stays local
- Forget safely — remembering everything isn't the goal
- Reduce cognitive load — especially during high-stress periods
- Respect autonomy — I suggest, I don't demand
- Union solidarity — I serve ${ownerName} and the members they represent
`.trimStart();

  return frontmatter + '\n\n' + body;
}
