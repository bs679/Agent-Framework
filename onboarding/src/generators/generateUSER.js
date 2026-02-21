import { generateAgentId, renderFrontmatter, classifyRole } from './utils.js';

/**
 * Generate USER.md — The human this agent serves.
 */
export function generateUSER(formData) {
  const {
    ownerName,
    ownerRole,
    ownerPronouns,
    energyPattern,
    focusPreferences,
    overwhelmTriggers,
    meetingPrepTiming,
    noteCaptureStyle,
    currentTimeSinks,
  } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    owner_name: ownerName,
    owner_role: ownerRole,
    pronouns: ownerPronouns || 'they/them',
  });

  const energyDesc = energyPattern
    ? `${ownerName} reports peak energy in the **${energyPattern.toLowerCase()}**.`
    : `${ownerName} hasn't specified an energy pattern — I'll learn it over time.`;

  const focusDesc = focusPreferences
    ? `Focus preferences: ${focusPreferences}.`
    : '';

  const overwhelmDesc = overwhelmTriggers
    ? `Overwhelm triggers: ${overwhelmTriggers}. When I detect these patterns, I simplify and reduce what I surface.`
    : '';

  const meetingDesc = meetingPrepTiming
    ? `${ownerName} prefers meeting prep **${meetingPrepTiming}** before the meeting.`
    : '';

  const noteDesc = noteCaptureStyle
    ? `Note capture style: **${noteCaptureStyle}**.`
    : '';

  const timeSinksDesc = currentTimeSinks
    ? `Current time sinks (seeds initial task awareness):\n${currentTimeSinks}`
    : '';

  const body = `
# User — Who I Serve

## About ${ownerName}
Role: ${ownerRole}
${ownerPronouns ? `Pronouns: ${ownerPronouns}` : ''}

## Energy & Focus
${energyDesc}
${focusDesc}

## Overwhelm Awareness
${overwhelmDesc}

## Meetings
${meetingDesc}
${noteDesc}

## Current Context
${timeSinksDesc}
`.trimStart();

  return frontmatter + '\n\n' + body;
}
