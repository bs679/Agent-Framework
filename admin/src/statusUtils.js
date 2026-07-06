// Status presentation helpers for the agent dashboard.
//
// Cross-cutting rule: no red. Status colors are green / yellow / orange /
// dim white only.

export const CONTAINER_STATES = {
  running: { mark: '✓', label: 'running', color: '#2e7d32' },
  stopped: { mark: '~', label: 'stopped', color: '#b58900' },
  missing: { mark: '!', label: 'missing', color: '#cb6d1b' },
  unavailable: { mark: '○', label: 'docker unavailable', color: '#9e9e9e' },
};

export function containerPresentation(state) {
  return CONTAINER_STATES[state] ?? CONTAINER_STATES.unavailable;
}

export function heartbeatLabel(slot) {
  if (!slot || !slot.completed) return '—';
  return slot.time || 'done';
}

// Aggregate health for the summary strip: how many agents are in each state.
export function summarize(agents) {
  const counts = { running: 0, stopped: 0, missing: 0, unavailable: 0 };
  for (const a of agents) {
    counts[a.container] = (counts[a.container] ?? 0) + 1;
  }
  return counts;
}
