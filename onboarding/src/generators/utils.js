/**
 * Shared utilities for all config file generators.
 */

/**
 * Slugify a string: lowercase, replace non-alphanumeric with hyphens, collapse multiples.
 */
function slugify(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Generate a 4-character random hex string.
 */
function randomHex4() {
  return Math.random().toString(16).slice(2, 6).padEnd(4, '0');
}

/**
 * Generate a unique agent_id from formData.
 * Format: {role-slug}-{name-slug}-{4-char-random}
 * Examples: president-dave-a3f2, sectreasurer-jane-b7k9
 *
 * The id is generated once and cached on the formData object so that all 6
 * generators produce identical ids within a single generation run.
 */
export function generateAgentId(formData) {
  if (formData._agentId) {
    return formData._agentId;
  }

  const roleSlug = slugify(formData.ownerRole || 'staff');
  const nameSlug = slugify(formData.ownerName || 'unknown');
  const id = `${roleSlug}-${nameSlug}-${randomHex4()}`;
  formData._agentId = id;
  return id;
}

/**
 * Map the vibe selection (Q11) to personality trait arrays.
 */
export const VIBE_TRAITS = {
  'Calm and supportive': ['patient', 'steady', 'encouraging', 'non-judgmental'],
  'Focused and efficient': ['direct', 'precise', 'efficient', 'results-oriented'],
  'Warm and collaborative': ['warm', 'collaborative', 'thoughtful', 'engaged'],
  'Adaptive': ['adaptive', 'perceptive', 'flexible', 'attentive'],
};

/**
 * Map energy pattern (Q4) to a canonical key.
 */
export function mapEnergyPattern(raw) {
  const lower = (raw || '').toLowerCase();
  if (lower.includes('morning') && !lower.includes('mid')) return 'morning';
  if (lower.includes('mid-morning') || lower.includes('mid morning') || lower.includes('late morning')) return 'mid-morning';
  if (lower.includes('afternoon')) return 'afternoon';
  if (lower.includes('evening') || lower.includes('night')) return 'evening';
  return 'variable';
}

/**
 * Map focus style (Q5) to a canonical key.
 */
export function mapFocusStyle(raw) {
  const lower = (raw || '').toLowerCase();
  if (lower.includes('deep') || lower.includes('block')) return 'deep_blocks';
  if (lower.includes('pomodoro') || lower.includes('timer') || lower.includes('25')) return 'pomodoro';
  return 'flow_based';
}

/**
 * Map information format (Q8) to a canonical key.
 */
export function mapInfoFormat(raw) {
  const lower = (raw || '').toLowerCase();
  if (lower.includes('bullet')) return 'bullets';
  if (lower.includes('prose') || lower.includes('paragraph')) return 'prose';
  if (lower.includes('table')) return 'tables';
  return 'mixed';
}

/**
 * Parse pronoun string into {subject, object, possessive}.
 */
export function parsePronouns(raw) {
  const lower = (raw || '').toLowerCase().trim();

  if (lower.startsWith('he')) {
    return { subject: 'he', object: 'him', possessive: 'his' };
  }
  if (lower.startsWith('she')) {
    return { subject: 'she', object: 'her', possessive: 'her' };
  }
  // Default: they/them/their for blank, "they/them", or anything unrecognized
  return { subject: 'they', object: 'them', possessive: 'their' };
}

/**
 * Derive 3-5 values from overall form responses.
 */
export function deriveValues(formData) {
  const values = [];

  // Always include core union values
  values.push('Solidarity with workers');

  // Derive from vibe
  const vibe = formData.vibeSelection || '';
  if (vibe.includes('Calm')) values.push('Patience and steadiness');
  if (vibe.includes('Focused')) values.push('Efficiency and clarity');
  if (vibe.includes('Warm')) values.push('Collaboration and care');
  if (vibe.includes('Adaptive')) values.push('Flexibility and responsiveness');

  // Derive from communication style
  const comm = (formData.communicationStyle || '').toLowerCase();
  if (comm.includes('direct') || comm.includes('brief')) {
    values.push('Respecting time and attention');
  } else if (comm.includes('detailed') || comm.includes('thorough')) {
    values.push('Thoroughness and accuracy');
  }

  // Derive from bad news approach
  const bad = (formData.badNewsApproach || '').toLowerCase();
  if (bad.includes('straight') || bad.includes('direct') || bad.includes('blunt')) {
    values.push('Honesty, even when it is hard');
  } else if (bad.includes('gentle') || bad.includes('soft') || bad.includes('careful')) {
    values.push('Compassion in hard conversations');
  }

  // Ensure at least 3
  if (values.length < 3) values.push('Transparency and trust');
  if (values.length < 3) values.push('Getting things done');

  return values.slice(0, 5);
}

/**
 * Build YAML frontmatter from an object. Values are serialized as YAML.
 */
export function buildFrontmatter(fields) {
  const lines = ['---'];
  for (const [key, value] of Object.entries(fields)) {
    if (Array.isArray(value)) {
      lines.push(`${key}:`);
      for (const item of value) {
        lines.push(`  - "${item}"`);
      }
    } else {
      lines.push(`${key}: "${value}"`);
    }
  }
  lines.push('---');
  return lines.join('\n');
}

/**
 * Split a freeform text block (Q17) into an array by newlines or sentences.
 */
export function splitTimeSinks(raw) {
  if (!raw) return [];
  return raw
    .split(/[\n;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}
