/**
 * Generator tests — run with: node --experimental-vm-modules src/generators/__tests__/run.js
 *
 * Tests all 6 generators across President, Secretary/Treasurer,
 * Executive Secretary, and Staff roles. Verifies:
 *   - All 6 files have matching agent_id values
 *   - MEMORY.md always includes all 5 required sensitive_categories
 *   - MEMORY.md always has encrypt_at_rest: true
 *   - AGENTS.md has correct collaboration mapping per role
 *   - HEARTBEAT.md has correct check-in times per energy pattern
 */

import { generateSOUL } from '../generateSOUL.js';
import { generateUSER } from '../generateUSER.js';
import { generateIDENTITY } from '../generateIDENTITY.js';
import { generateAGENTS } from '../generateAGENTS.js';
import { generateHEARTBEAT } from '../generateHEARTBEAT.js';
import { generateMEMORY } from '../generateMEMORY.js';
import { generateAgentId } from '../utils.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  PASS: ${message}`);
  } else {
    failed++;
    console.error(`  FAIL: ${message}`);
  }
}

function extractFrontmatterField(content, field) {
  const regex = new RegExp(`^${field}:\\s*"?([^"\\n]+)"?`, 'm');
  const match = content.match(regex);
  return match ? match[1] : null;
}

function extractFrontmatterArray(content, field) {
  const lines = content.split('\n');
  const items = [];
  let capturing = false;
  for (const line of lines) {
    if (line.startsWith(`${field}:`)) {
      capturing = true;
      continue;
    }
    if (capturing) {
      const itemMatch = line.match(/^\s+-\s+"?([^"]+)"?/);
      if (itemMatch) {
        items.push(itemMatch[1]);
      } else {
        break;
      }
    }
  }
  return items;
}

// --- Test scenarios ---

const TEST_CASES = [
  {
    label: 'President (Dave)',
    formData: {
      ownerName: 'Dave',
      ownerRole: 'President',
      ownerPronouns: 'he/him',
      energyPattern: 'Early morning',
      focusPreferences: 'No interruptions before 10am',
      overwhelmTriggers: 'Too many unread emails',
      communicationTone: 'Calm and direct',
      communicationFormat: 'Bullet points',
      badNewsDelivery: 'Lead with the facts, then offer options',
      agentName: 'Franklin',
      agentPersonality: 'Steady and methodical',
      meetingPrepTiming: '1 hour before',
      noteCaptureStyle: 'Key decisions and action items only',
      currentTimeSinks: 'Contract negotiations prep',
    },
    expectedRole: 'president',
  },
  {
    label: 'Secretary/Treasurer',
    formData: {
      ownerName: 'Maria',
      ownerRole: 'Secretary/Treasurer',
      ownerPronouns: 'she/her',
      energyPattern: 'Mid-morning',
      focusPreferences: '',
      overwhelmTriggers: 'Budget season',
      communicationTone: 'Professional and concise',
      communicationFormat: 'Short paragraphs',
      badNewsDelivery: 'Be blunt — just tell me',
      agentName: '',
      agentPersonality: 'Crisp and efficient',
      meetingPrepTiming: 'Morning of the meeting',
      noteCaptureStyle: 'Detailed minutes',
      currentTimeSinks: 'Dues reconciliation',
    },
    expectedRole: 'sectreasurer',
  },
  {
    label: 'Executive Secretary',
    formData: {
      ownerName: 'James',
      ownerRole: 'Executive Secretary',
      ownerPronouns: 'he/him',
      energyPattern: 'Afternoon',
      focusPreferences: 'Deep work in the afternoon',
      overwhelmTriggers: 'Back-to-back meetings',
      communicationTone: 'Warm and supportive',
      communicationFormat: 'Detailed narrative',
      badNewsDelivery: 'Soften it first, then give me the details',
      agentName: 'Atlas',
      agentPersonality: 'Warm and encouraging',
      meetingPrepTiming: 'Day before',
      noteCaptureStyle: 'Bullet summary after the meeting',
      currentTimeSinks: 'Catching up on minutes backlog',
    },
    expectedRole: 'execsecretary',
  },
  {
    label: 'Staff member',
    formData: {
      ownerName: 'Pat',
      ownerRole: 'Staff',
      ownerPronouns: 'they/them',
      energyPattern: 'Evening',
      focusPreferences: '',
      overwhelmTriggers: '',
      communicationTone: 'Casual and friendly',
      communicationFormat: 'Just the essentials',
      badNewsDelivery: 'Ask me if now is a good time first',
      agentName: '',
      agentPersonality: 'Curious and proactive',
      meetingPrepTiming: '15 minutes before',
      noteCaptureStyle: 'I handle my own notes',
      currentTimeSinks: '',
    },
    expectedRole: 'staff',
  },
];

const REQUIRED_SENSITIVE = [
  'member_data',
  'grievance_details',
  'negotiation_strategy',
  'financial_account_info',
  'executive_session_content',
];

const ENERGY_TIMES = {
  'Early morning': { morning: '07:00', evening: '17:00' },
  'Mid-morning':   { morning: '08:30', evening: '17:30' },
  'Afternoon':     { morning: '09:00', evening: '18:00' },
  'Evening':       { morning: '09:00', evening: '19:00' },
  'It varies':     { morning: '08:00', evening: '17:00' },
};

const ROLE_COLLABS = {
  president:     ['sectreasurer-*', 'execsecretary-*'],
  sectreasurer:  ['president-*'],
  execsecretary: ['president-*', 'sectreasurer-*'],
  staff:         ['execsecretary-*'],
};

const ROLE_ESCALATION = {
  president: 'self — President is top of escalation chain',
  sectreasurer: 'president-*',
  execsecretary: 'president-*',
  staff: 'execsecretary-*',
};

// --- Run tests ---

for (const tc of TEST_CASES) {
  console.log(`\n=== ${tc.label} ===`);

  const soul = generateSOUL(tc.formData);
  const user = generateUSER(tc.formData);
  const identity = generateIDENTITY(tc.formData);
  const agents = generateAGENTS(tc.formData);
  const heartbeat = generateHEARTBEAT(tc.formData);
  const memory = generateMEMORY(tc.formData);

  const expectedAgentId = generateAgentId(tc.formData.ownerName, tc.formData.ownerRole);

  // 1. All 6 files have matching agent_id
  const files = { SOUL: soul, USER: user, IDENTITY: identity, AGENTS: agents, HEARTBEAT: heartbeat, MEMORY: memory };
  for (const [name, content] of Object.entries(files)) {
    const id = extractFrontmatterField(content, 'agent_id');
    assert(id === expectedAgentId, `${name}.md agent_id = "${id}" matches expected "${expectedAgentId}"`);
  }

  // 2. MEMORY.md: encrypt_at_rest is always true
  assert(
    memory.includes('encrypt_at_rest: true'),
    'MEMORY.md has encrypt_at_rest: true'
  );

  // 3. MEMORY.md: all 5 required sensitive_categories present
  const memoryCategories = extractFrontmatterArray(memory, 'sensitive_categories');
  for (const cat of REQUIRED_SENSITIVE) {
    assert(
      memoryCategories.includes(cat),
      `MEMORY.md sensitive_categories includes "${cat}"`
    );
  }

  // 4. AGENTS.md: correct collaborates_with
  const agentsCollabs = extractFrontmatterArray(agents, 'collaborates_with');
  const expectedCollabs = ROLE_COLLABS[tc.expectedRole];
  assert(
    JSON.stringify(agentsCollabs) === JSON.stringify(expectedCollabs),
    `AGENTS.md collaborates_with = ${JSON.stringify(agentsCollabs)} matches expected ${JSON.stringify(expectedCollabs)}`
  );

  // 5. AGENTS.md: correct escalation_path
  const escalation = extractFrontmatterField(agents, 'escalation_path');
  assert(
    escalation === ROLE_ESCALATION[tc.expectedRole],
    `AGENTS.md escalation_path = "${escalation}" matches expected`
  );

  // 6. HEARTBEAT.md: correct check-in times for energy pattern
  const expectedTimes = ENERGY_TIMES[tc.formData.energyPattern];
  const morningTime = extractFrontmatterField(heartbeat, 'morning_checkin_time');
  const eveningTime = extractFrontmatterField(heartbeat, 'evening_checkin_time');
  assert(
    morningTime === expectedTimes.morning,
    `HEARTBEAT.md morning_checkin_time = "${morningTime}" matches expected "${expectedTimes.morning}"`
  );
  assert(
    eveningTime === expectedTimes.evening,
    `HEARTBEAT.md evening_checkin_time = "${eveningTime}" matches expected "${expectedTimes.evening}"`
  );

  // 7. HEARTBEAT.md: has role-specific triggers
  if (tc.expectedRole === 'president') {
    assert(heartbeat.includes('grievance_deadline_7d'), 'HEARTBEAT.md includes president trigger: grievance_deadline_7d');
    assert(heartbeat.includes('legislative_hearing_upcoming'), 'HEARTBEAT.md includes president trigger: legislative_hearing_upcoming');
    assert(heartbeat.includes('board_meeting_approaching'), 'HEARTBEAT.md includes president trigger: board_meeting_approaching');
  } else if (tc.expectedRole === 'sectreasurer') {
    assert(heartbeat.includes('disbursement_pending_cosignature'), 'HEARTBEAT.md includes sectreasurer trigger: disbursement_pending_cosignature');
    assert(heartbeat.includes('dues_remittance_due'), 'HEARTBEAT.md includes sectreasurer trigger: dues_remittance_due');
    assert(heartbeat.includes('budget_variance_alert'), 'HEARTBEAT.md includes sectreasurer trigger: budget_variance_alert');
  } else if (tc.expectedRole === 'execsecretary') {
    assert(heartbeat.includes('minutes_approval_pending'), 'HEARTBEAT.md includes execsecretary trigger: minutes_approval_pending');
    assert(heartbeat.includes('meeting_scheduling_conflict'), 'HEARTBEAT.md includes execsecretary trigger: meeting_scheduling_conflict');
    assert(heartbeat.includes('correspondence_followup_due'), 'HEARTBEAT.md includes execsecretary trigger: correspondence_followup_due');
  }

  // 8. HEARTBEAT.md body: human-readable trigger descriptions
  assert(heartbeat.includes('A deadline is approaching within 48 hours'), 'HEARTBEAT.md body has human-readable trigger for deadline_approaching_48h');

  // 9. AGENTS.md: President escalation text
  if (tc.expectedRole === 'president') {
    assert(
      agents.includes("I am the top of the escalation chain"),
      'AGENTS.md body has President escalation text'
    );
  } else {
    assert(
      agents.includes("If I encounter something outside my authority"),
      'AGENTS.md body has non-President escalation text'
    );
  }

  // 10. AGENTS.md: always mentions co-signature boundary
  assert(
    agents.includes('co-signature is always required'),
    'AGENTS.md body includes co-signature boundary'
  );

  // 11. MEMORY.md: forget on request
  assert(
    memory.includes('forget_on_request: true'),
    'MEMORY.md has forget_on_request: true'
  );

  // 12. MEMORY.md body: mentions all 5 sensitive categories in prose
  assert(memory.includes('Member personal data'), 'MEMORY.md body mentions member data');
  assert(memory.includes('Grievance case details'), 'MEMORY.md body mentions grievance details');
  assert(memory.includes('Contract negotiation strategy'), 'MEMORY.md body mentions negotiation strategy');
  assert(memory.includes('Financial account information'), 'MEMORY.md body mentions financial info');
  assert(memory.includes('Executive session content'), 'MEMORY.md body mentions executive session content');
}

// --- Summary ---
console.log(`\n${'='.repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed, ${passed + failed} total`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log('All tests passed.');
}
