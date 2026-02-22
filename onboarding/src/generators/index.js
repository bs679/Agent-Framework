import { generateAgentId } from './utils.js';
import { generateSOUL } from './generateSOUL.js';
import { generateUSER } from './generateUSER.js';
import { generateIDENTITY } from './generateIDENTITY.js';
import { generateAGENTS } from './generateAGENTS.js';
import { generateHEARTBEAT } from './generateHEARTBEAT.js';
import { generateMEMORY } from './generateMEMORY.js';

export {
  generateAgentId,
  generateSOUL,
  generateUSER,
  generateIDENTITY,
  generateAGENTS,
  generateHEARTBEAT,
  generateMEMORY,
};

/**
 * Run all 6 generators against the same formData and return a map of
 * filename → content. The agent_id is guaranteed identical across all files
 * because generateAgentId caches on the formData object.
 */
export function generateAll(formData) {
  // Clear any cached id so a fresh run gets a fresh id
  delete formData._agentId;

  return {
    'SOUL.md': generateSOUL(formData),
    'USER.md': generateUSER(formData),
    'IDENTITY.md': generateIDENTITY(formData),
    'AGENTS.md': generateAGENTS(formData),
    'HEARTBEAT.md': generateHEARTBEAT(formData),
    'MEMORY.md': generateMEMORY(formData),
  };
}
