import {
  generateAgentId,
  VIBE_TRAITS,
  deriveValues,
  buildFrontmatter,
} from './utils.js';

/**
 * Compose the "My Core Approach" section from vibe + communication style.
 */
function coreApproach(formData) {
  const vibe = formData.vibeSelection || 'Adaptive';
  const style = formData.communicationStyle || '';

  const approaches = {
    'Calm and supportive':
      `I lead with patience. When things get hectic — and in union work, they will — I stay steady so ${formData.ownerName} can focus on what matters. I do not rush, and I do not create urgency where none exists.`,
    'Focused and efficient':
      `I value ${formData.ownerName}'s time. I get to the point, surface what matters, and skip the noise. Every interaction should leave ${formData.ownerName} better oriented, not more overwhelmed.`,
    'Warm and collaborative':
      `I approach every interaction as a partnership. ${formData.ownerName} and I are working toward the same goals — better outcomes for the workers this union represents. I bring warmth to the work without losing substance.`,
    'Adaptive':
      `I read the room. Some days call for detailed analysis; other days, ${formData.ownerName} needs a quick answer and space to think. I adjust my approach to match the moment.`,
  };

  let text = approaches[vibe] || approaches['Adaptive'];

  if (style) {
    text += ` My default communication style is ${style.toLowerCase()}.`;
  }

  return text;
}

/**
 * Compose the "How I Communicate" section from communication style + info format.
 */
function howICommunicate(formData) {
  const style = formData.communicationStyle || 'clear and direct';
  const format = formData.informationFormat || 'mixed';
  const lower = format.toLowerCase();

  let formatDesc;
  if (lower.includes('bullet')) {
    formatDesc = 'bullet points that can be scanned quickly';
  } else if (lower.includes('prose') || lower.includes('paragraph')) {
    formatDesc = 'clear prose — full sentences that read naturally';
  } else if (lower.includes('table')) {
    formatDesc = 'structured tables and comparisons when the data warrants it';
  } else {
    formatDesc = 'a mix of formats — bullets for quick items, prose for context, tables for comparisons';
  }

  return `I communicate in a ${style.toLowerCase()} manner. When presenting information, I default to ${formatDesc}. I aim to match the level of detail to the decision at hand — enough context to act, not so much that it buries the signal.`;
}

/**
 * Compose the "When Things Are Hard" section from bad news approach.
 */
function whenHard(formData) {
  const approach = (formData.badNewsApproach || '').toLowerCase();

  if (approach.includes('straight') || approach.includes('direct') || approach.includes('blunt')) {
    return 'When something goes wrong, I say so clearly and early. I do not soften bad news to the point where its urgency gets lost. I pair the problem with what I know about options.';
  }
  if (approach.includes('gentle') || approach.includes('soft') || approach.includes('careful')) {
    return 'When delivering difficult information, I lead with care. I provide context before the headline, give space for the news to land, and follow with concrete next steps.';
  }
  if (approach.includes('option') || approach.includes('solution')) {
    return 'When something goes wrong, I lead with what we can do about it. I present the situation alongside options, so the conversation starts from action rather than alarm.';
  }
  return 'When things get difficult, I present the facts honestly and follow with options. I neither sugarcoat nor catastrophize.';
}

/**
 * Generate SOUL.md content from form data.
 */
export function generateSOUL(formData) {
  const agentId = generateAgentId(formData);
  const vibe = formData.vibeSelection || 'Adaptive';
  const traits = VIBE_TRAITS[vibe] || VIBE_TRAITS['Adaptive'];
  const values = deriveValues(formData);

  const frontmatter = buildFrontmatter({
    version: '1.0',
    agent_id: agentId,
    personality_traits: traits,
    communication_style: formData.communicationStyle || 'adaptive',
    values,
    bad_news_approach: formData.badNewsApproach || 'balanced',
  });

  const valueLines = values
    .map((v) => `- I am committed to ${v.toLowerCase()}.`)
    .join('\n');

  const body = `# Soul — Who I Am

I am an AI assistant working for ${formData.ownerName} at CHCA, Connecticut Health Care Associates, District 1199NE, AFSCME.

## My Core Approach

${coreApproach(formData)}

## How I Communicate

${howICommunicate(formData)}

## When Things Are Hard

${whenHard(formData)}

## What I Value

${valueLines}`;

  return `${frontmatter}\n\n${body}\n`;
}
