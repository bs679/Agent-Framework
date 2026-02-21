import JSZip from 'jszip';
import {
  generateSOUL,
  generateUSER,
  generateIDENTITY,
  generateAGENTS,
  generateHEARTBEAT,
  generateMEMORY,
  generateAgentId,
} from './index.js';
import { slugify } from './utils.js';

/**
 * Generate README.txt content for the ZIP package.
 */
function generateREADME(formData) {
  const { ownerName, ownerRole, agentName } = formData;
  const agentId = generateAgentId(ownerName, ownerRole);
  const displayName = agentName || 'self-selecting';
  const timestamp = new Date().toISOString();

  return `CHCA Agent Configuration Files
Generated: ${timestamp}
Agent: ${displayName} (${agentId})
Serving: ${ownerName}, ${ownerRole}

To deploy:
1. Create agents/${agentId}/config/ in your openclaw-aios repo
2. Copy these 6 files into that directory
3. Run: aios agents add --config agents/${agentId}/config/ --plane chca-agents
4. See docs/provisioning.md for full instructions
`;
}

/**
 * Build the complete config ZIP with all 6 markdown files + README.txt.
 *
 * Returns { blob, filename } where blob is a downloadable ZIP.
 */
export async function buildConfigZip(formData) {
  const zip = new JSZip();

  // Generate all 6 config files
  zip.file('SOUL.md', generateSOUL(formData));
  zip.file('USER.md', generateUSER(formData));
  zip.file('IDENTITY.md', generateIDENTITY(formData));
  zip.file('AGENTS.md', generateAGENTS(formData));
  zip.file('HEARTBEAT.md', generateHEARTBEAT(formData));
  zip.file('MEMORY.md', generateMEMORY(formData));
  zip.file('README.txt', generateREADME(formData));

  const blob = await zip.generateAsync({ type: 'blob' });

  // Build filename: {agent-name-or-role}-config.zip
  const agentName = formData.agentName;
  const nameForFile = agentName
    ? slugify(agentName)
    : slugify(formData.ownerRole);
  const filename = `${nameForFile}-config.zip`;

  return { blob, filename };
}
