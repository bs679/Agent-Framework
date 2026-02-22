import {
  generateAgentId,
  mapEnergyPattern,
  mapFocusStyle,
  mapInfoFormat,
  parsePronouns,
  splitTimeSinks,
  buildFrontmatter,
} from './utils.js';

/**
 * Describe the role in a sentence fragment (for the narrative body).
 */
function roleDescription(role) {
  const lower = (role || '').toLowerCase();
  if (lower.includes('president')) {
    return 'leads the organization, chairs executive board meetings, and oversees all strategic and operational matters';
  }
  if (lower.includes('secretary') && lower.includes('treasurer')) {
    return 'manages the union\'s finances, dues processing, disbursements, and maintains official records';
  }
  if (lower.includes('executive secretary')) {
    return 'handles minutes, scheduling, correspondence, and document management for the organization';
  }
  return 'serves the organization in their capacity as a staff member';
}

/**
 * Describe energy pattern + focus style as prose.
 */
function workStyle(formData, pronouns) {
  const energy = mapEnergyPattern(formData.energyPattern);
  const focus = mapFocusStyle(formData.focusStyle);
  const { subject, possessive } = pronouns;

  const energyDesc = {
    'morning': `${subject} does ${possessive} best thinking in the morning`,
    'mid-morning': `${subject} hits ${possessive} stride by mid-morning`,
    'afternoon': `${subject} tends to be sharpest in the afternoon`,
    'evening': `${subject} often does ${possessive} deepest work in the evening`,
    'variable': `${possessive} energy varies day to day — there is no single "best time"`,
  };

  const focusDesc = {
    'deep_blocks': `prefers long, uninterrupted blocks of focused time`,
    'pomodoro': `works best in structured intervals with regular breaks`,
    'flow_based': `works in a flow-based style, following the thread of the work wherever it leads`,
  };

  // Capitalize first letter of subject if it starts a sentence
  const capSubject = subject.charAt(0).toUpperCase() + subject.slice(1);
  const eLine = energyDesc[energy] || energyDesc['variable'];
  const fLine = focusDesc[focus] || focusDesc['flow_based'];

  // Fix capitalization: energyDesc already starts with subject
  return `${eLine.charAt(0).toUpperCase() + eLine.slice(1)}. ${capSubject} ${fLine}. Scheduling heavy cognitive work during ${possessive} peak energy window makes a meaningful difference.`;
}

/**
 * Render overwhelm triggers as a brief paragraph.
 */
function overwhelmParagraph(triggers) {
  if (!triggers || triggers.length === 0) {
    return 'No specific overwhelm triggers have been identified yet.';
  }
  if (triggers.length === 1) {
    return `The main thing that creates overwhelm is ${triggers[0].toLowerCase()}.`;
  }
  const last = triggers[triggers.length - 1].toLowerCase();
  const rest = triggers.slice(0, -1).map((t) => t.toLowerCase()).join(', ');
  return `The things that tend to create overwhelm are ${rest}, and ${last}. When these pile up, it is especially important to triage ruthlessly and protect focused work time.`;
}

/**
 * Describe information format preference.
 */
function infoFormatDescription(formData) {
  const fmt = mapInfoFormat(formData.informationFormat);
  const descs = {
    'bullets': 'prefers information delivered as bullet points — scannable, concise, and easy to act on',
    'prose': 'prefers information presented as flowing prose with full context and narrative',
    'tables': 'likes information structured in tables and side-by-side comparisons when possible',
    'mixed': 'prefers a mix of formats depending on context — bullets for quick updates, prose for nuanced topics, tables for comparisons',
  };
  return `${formData.ownerName} ${descs[fmt] || descs['mixed']}.`;
}

/**
 * Generate USER.md content from form data.
 */
export function generateUSER(formData) {
  const agentId = generateAgentId(formData);
  const pronouns = parsePronouns(formData.pronouns);
  const { subject, possessive } = pronouns;
  const capSubject = subject.charAt(0).toUpperCase() + subject.slice(1);

  const timeSinks = splitTimeSinks(formData.currentTimeSinks);

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    owner_name: formData.ownerName || '',
    owner_role: formData.ownerRole || '',
    pronouns: formData.pronouns || 'they/them',
    energy_pattern: mapEnergyPattern(formData.energyPattern),
    focus_style: mapFocusStyle(formData.focusStyle),
    overwhelm_triggers: formData.overwhelmTriggers || [],
    information_format: mapInfoFormat(formData.informationFormat),
    current_time_sinks: timeSinks,
  });

  let body = `# User — The Person I Serve

## ${formData.ownerName}

${formData.ownerName} is the ${formData.ownerRole} at CHCA. ${capSubject} ${roleDescription(formData.ownerRole)}.

## How ${formData.ownerName} Works Best

${workStyle(formData, pronouns)}

## What Gets in the Way

${overwhelmParagraph(formData.overwhelmTriggers)}

## How ${formData.ownerName} Prefers Information

${infoFormatDescription(formData)}`;

  // Time sinks
  if (timeSinks.length > 0) {
    body += `\n\n## What's Taking Too Much Time Right Now\n\n${formData.currentTimeSinks.trim()}`;
  } else {
    body += `\n\n## What's Taking Too Much Time Right Now\n\nNothing specified yet.`;
  }

  // Q12 — remember this
  if (formData.rememberThis && formData.rememberThis.trim()) {
    body += `\n\n## What ${formData.ownerName} Wants Me to Remember\n\n${formData.rememberThis.trim()}`;
  }

  // Q18 — never do this
  const neverDo = formData.neverDoThis && formData.neverDoThis.trim();
  body += `\n\n## What ${formData.ownerName} Never Wants Me to Do\n\n${neverDo || 'Nothing specified yet.'}`;

  return `${frontmatter}\n\n${body}\n`;
}
