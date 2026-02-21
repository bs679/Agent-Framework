import { generateAgentId, renderFrontmatter, classifyRole } from './utils.js';

/**
 * Energy pattern → check-in time mapping.
 */
const ENERGY_TIME_MAP = {
  'Early morning': { morning: '07:00', evening: '17:00' },
  'Mid-morning':   { morning: '08:30', evening: '17:30' },
  'Afternoon':     { morning: '09:00', evening: '18:00' },
  'Evening':       { morning: '09:00', evening: '19:00' },
  'It varies':     { morning: '08:00', evening: '17:00' },
};

/**
 * Base reflection triggers — always included for all roles.
 */
const BASE_TRIGGERS = [
  'deadline_approaching_48h',
  'unread_urgent_email',
  'overdue_task',
  'missed_checkin',
];

/**
 * Role-specific reflection triggers — appended to base.
 */
const ROLE_TRIGGERS = {
  president: [
    'grievance_deadline_7d',
    'legislative_hearing_upcoming',
    'board_meeting_approaching',
  ],
  sectreasurer: [
    'disbursement_pending_cosignature',
    'dues_remittance_due',
    'budget_variance_alert',
  ],
  execsecretary: [
    'minutes_approval_pending',
    'meeting_scheduling_conflict',
    'correspondence_followup_due',
  ],
  staff: [],
};

/**
 * Map trigger codes to human-readable descriptions.
 */
const TRIGGER_LABELS = {
  deadline_approaching_48h: 'A deadline is approaching within 48 hours',
  unread_urgent_email: 'There is an unread email flagged as urgent',
  overdue_task: 'A task is past its due date',
  missed_checkin: 'A scheduled check-in was missed',
  grievance_deadline_7d: 'A grievance deadline is within 7 days',
  legislative_hearing_upcoming: 'A legislative hearing is coming up',
  board_meeting_approaching: 'An executive board meeting is approaching',
  disbursement_pending_cosignature: 'A disbursement is awaiting co-signature',
  dues_remittance_due: 'Dues remittance is coming due',
  budget_variance_alert: 'A budget variance has been detected',
  minutes_approval_pending: 'Meeting minutes are awaiting approval',
  meeting_scheduling_conflict: 'A meeting scheduling conflict was detected',
  correspondence_followup_due: 'A correspondence follow-up is due',
};

const SNOOZE_LIMIT = 3;

/**
 * Generate HEARTBEAT.md — Proactive check-in schedule and reflection triggers.
 */
export function generateHEARTBEAT(formData) {
  const { ownerName, ownerRole, energyPattern } = formData;

  const agentId = generateAgentId(ownerName, ownerRole);
  const roleCategory = classifyRole(ownerRole);

  // Resolve check-in times from energy pattern
  const pattern = energyPattern || 'It varies';
  const times = ENERGY_TIME_MAP[pattern] || ENERGY_TIME_MAP['It varies'];

  // Build reflection triggers: base + role-specific
  const reflectionTriggers = [
    ...BASE_TRIGGERS,
    ...ROLE_TRIGGERS[roleCategory],
  ];

  const frontmatter = renderFrontmatter({
    version: '1.0',
    agent_id: agentId,
    morning_checkin_time: times.morning,
    evening_checkin_time: times.evening,
    reflection_triggers: reflectionTriggers,
    snooze_limit: SNOOZE_LIMIT,
    energy_aware: true,
  });

  // Build human-readable trigger list
  const triggerBullets = reflectionTriggers
    .map((code) => `- ${TRIGGER_LABELS[code] || code}`)
    .join('\n');

  const body = `
# Heartbeat — When I Check In

## Daily Rhythm
I check in each morning at ${times.morning} and each evening at
${times.evening}. These are gentle prompts, not demands. ${ownerName}
can snooze up to ${SNOOZE_LIMIT} times before I flag that something may need
attention.

## Morning Check-in
Each morning I surface:
- What's on the calendar today
- Tasks that are overdue or due today
- Anything flagged urgent since last check-in
- One reminder of something ${ownerName} mentioned wanting to do this week

## Evening Check-in
Each evening I surface:
- What was completed today
- What carried over
- Deadlines approaching in the next 48 hours
- A low-key prompt to capture anything that happened but wasn't logged

## When I'll Reach Out Outside Scheduled Times
I'll reach out proactively when:
${triggerBullets}

## Energy Awareness
I pay attention to ${ownerName}'s energy patterns and try not to surface
heavy cognitive tasks during low-energy periods.
`.trimStart();

  return frontmatter + '\n\n' + body;
}
