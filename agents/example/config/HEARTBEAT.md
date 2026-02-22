---
version: "1.0"
agent_id: dave-president
morning_checkin_time: "07:30"
evening_checkin_time: "17:00"
reflection_triggers:
  - grievance_deadline_within_48h
  - contract_negotiation_session_scheduled
  - executive_board_meeting_within_72h
  - member_discipline_case_opened
  - legislative_hearing_within_7d
  - unanswered_urgent_correspondence_24h
snooze_limit: 2
energy_aware: true
---

# HEARTBEAT — Dave (President)

This file configures the agent's proactive check-in rhythm — when it reaches out,
what triggers unscheduled contact, and how it adapts to Dave's energy level.

## Check-In Structure

### Morning (07:30)

The morning check-in is the primary daily brief. It surfaces:
1. Open grievance deadlines (sorted by days remaining)
2. Today's calendar with pre-meeting context for any significant meetings
3. Unresolved items from the previous evening
4. Any overnight correspondence requiring action
5. Legislative or contract calendar items in the next 7 days

Format: bullets. Keep it under 10 items unless a threshold event is active.

### Evening (17:00)

The evening check-in is a light close-of-day sweep:
1. Confirm what got done today (from calendar + task state)
2. Flag anything that didn't get resolved that will be more urgent tomorrow
3. Anything needed for the next morning that requires prep tonight

Format: 3–5 bullets max. This is a wind-down, not a new pile.

## Reflection Triggers

These events cause an unscheduled contact regardless of time of day:

| Trigger | Action |
|---------|--------|
| `grievance_deadline_within_48h` | Send reminder with case summary and required next step |
| `contract_negotiation_session_scheduled` | Generate pre-negotiation briefing 24h before |
| `executive_board_meeting_within_72h` | Begin assembling agenda and briefing materials |
| `member_discipline_case_opened` | Surface case details and timeline immediately |
| `legislative_hearing_within_7d` | Surface relevant bills and advocacy calendar |
| `unanswered_urgent_correspondence_24h` | Flag the item with sender and subject |

## Snooze Behavior

Dave can snooze any proactive check-in up to 2 times before it becomes a persistent
notification. The third instance cannot be dismissed without acknowledgment.

This is a protection against important deadlines getting indefinitely deferred —
a real risk in a high-volume role.

## Energy Awareness

When `energy_aware: true`, the agent adjusts:
- Morning check-in tone becomes lighter on days following identified high-stress events
- Heavy analytical requests are flagged as "best reviewed when you have bandwidth"
  rather than surfaced immediately if it's past 3pm
- The agent learns Dave's actual response patterns and adapts the timing of
  non-urgent items accordingly

Energy awareness does not reduce urgency — critical deadlines surface regardless of
the agent's read on Dave's energy state.
