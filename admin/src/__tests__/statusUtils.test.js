import { describe, expect, it } from 'vitest';
import {
  CONTAINER_STATES,
  containerPresentation,
  heartbeatLabel,
  summarize,
} from '../statusUtils.js';

describe('containerPresentation', () => {
  it('maps each known state to a mark and color', () => {
    expect(containerPresentation('running').mark).toBe('✓');
    expect(containerPresentation('stopped').mark).toBe('~');
    expect(containerPresentation('missing').mark).toBe('!');
    expect(containerPresentation('unavailable').mark).toBe('○');
  });

  it('falls back to unavailable for unknown states', () => {
    expect(containerPresentation('weird')).toBe(CONTAINER_STATES.unavailable);
  });

  it('never uses red (cross-cutting rule)', () => {
    for (const { color } of Object.values(CONTAINER_STATES)) {
      expect(color.toLowerCase()).not.toMatch(/^#(f00|ff0000|e[0-9a-f]0000)/);
      expect(color.toLowerCase()).not.toBe('red');
    }
  });
});

describe('heartbeatLabel', () => {
  it('shows a dash when not completed', () => {
    expect(heartbeatLabel({ completed: false, time: null })).toBe('—');
    expect(heartbeatLabel(null)).toBe('—');
  });

  it('shows the time when completed', () => {
    expect(heartbeatLabel({ completed: true, time: '07:02' })).toBe('07:02');
  });

  it('falls back to "done" when completed without a time', () => {
    expect(heartbeatLabel({ completed: true, time: null })).toBe('done');
  });
});

describe('summarize', () => {
  it('counts agents per container state', () => {
    const agents = [
      { container: 'running' },
      { container: 'running' },
      { container: 'stopped' },
      { container: 'missing' },
    ];
    expect(summarize(agents)).toEqual({
      running: 2,
      stopped: 1,
      missing: 1,
      unavailable: 0,
    });
  });

  it('handles the empty plane', () => {
    expect(summarize([])).toEqual({
      running: 0,
      stopped: 0,
      missing: 0,
      unavailable: 0,
    });
  });
});
