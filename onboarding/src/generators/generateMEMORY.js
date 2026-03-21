import { generateAgentId, buildFrontmatter } from './utils.js';

/**
 * Stub generator for MEMORY.md — Phase 3b.
 * Defines long-term memory schema, what to remember, what to forget.
 */
export function generateMEMORY(formData) {
  const agentId = generateAgentId(formData);

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    status: 'stub — Phase 3b',
  });

  const body = `# Memory — What I Keep and What I Let Go

> This file will be generated in Phase 3b. It will define the long-term memory
> schema, retention policies, and forgetting rules for this agent.`;

  return `${frontmatter}\n\n${body}\n`;
}
