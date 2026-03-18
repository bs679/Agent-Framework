import { generateAgentId, buildFrontmatter } from './utils.js';

/**
 * Stub generator for AGENTS.md — Phase 3b.
 * Describes how this agent collaborates with other agents in the plane.
 */
export function generateAGENTS(formData) {
  const agentId = generateAgentId(formData);

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    status: 'stub — Phase 3b',
  });

  const body = `# Agents — How I Work With Others

> This file will be generated in Phase 3b. It will describe how this agent
> collaborates with the other agents in the CHCA agents plane.`;

  return `${frontmatter}\n\n${body}\n`;
}
