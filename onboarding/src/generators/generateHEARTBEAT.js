import { generateAgentId, buildFrontmatter } from './utils.js';

/**
 * Stub generator for HEARTBEAT.md — Phase 3b.
 * Defines proactive check-in schedule, reflection triggers, energy patterns.
 */
export function generateHEARTBEAT(formData) {
  const agentId = generateAgentId(formData);

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    status: 'stub — Phase 3b',
  });

  const body = `# Heartbeat — When I Check In

> This file will be generated in Phase 3b. It will define the proactive check-in
> schedule, reflection triggers, and energy-aware timing for this agent.`;

  return `${frontmatter}\n\n${body}\n`;
}
