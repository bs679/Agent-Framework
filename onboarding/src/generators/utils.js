/**
 * Shared utilities for config file generators.
 */

/**
 * Generate a deterministic agent ID from role and owner name.
 * Format: {role-slug}-{name-slug}-{4-char hash}
 * Example: "president-dave-a3f1"
 */
export function generateAgentId(ownerName, ownerRole) {
  const roleSlug = slugify(ownerRole);
  const nameSlug = slugify(ownerName);
  const hash = simpleHash(`${roleSlug}-${nameSlug}`);
  return `${roleSlug}-${nameSlug}-${hash}`;
}

/**
 * Convert a string to a URL-safe slug.
 */
export function slugify(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Simple 4-char hex hash for agent ID suffix.
 */
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16).slice(0, 4).padStart(4, '0');
}

/**
 * Render YAML frontmatter from a plain object.
 * Handles strings, numbers, booleans, and arrays.
 */
export function renderFrontmatter(fields) {
  const lines = ['---'];
  for (const [key, value] of Object.entries(fields)) {
    if (Array.isArray(value)) {
      lines.push(`${key}:`);
      for (const item of value) {
        lines.push(`  - "${item}"`);
      }
    } else if (typeof value === 'string') {
      lines.push(`${key}: "${value}"`);
    } else {
      lines.push(`${key}: ${value}`);
    }
  }
  lines.push('---');
  return lines.join('\n');
}

/**
 * Determine the role category for collaboration/escalation mapping.
 * Returns one of: "president", "sectreasurer", "execsecretary", "staff"
 */
export function classifyRole(ownerRole) {
  const role = ownerRole.toLowerCase();
  if (role.includes('president') && !role.includes('vice')) {
    return 'president';
  }
  if (role.includes('secretary/treasurer') || role.includes('sec/treas') || role.includes('sectreasurer') || role.includes('treasurer')) {
    return 'sectreasurer';
  }
  if (role.includes('executive secretary') || role.includes('exec sec') || role.includes('execsecretary')) {
    return 'execsecretary';
  }
  return 'staff';
}
