import { describe, it, expect, beforeEach } from 'vitest';
import {
  generateAgentId,
  VIBE_TRAITS,
  mapEnergyPattern,
  mapFocusStyle,
  mapInfoFormat,
  parsePronouns,
  deriveValues,
  buildFrontmatter,
  splitTimeSinks,
} from '../utils.js';

describe('generateAgentId', () => {
  it('produces {role-slug}-{name-slug}-{4-char} format', () => {
    const fd = { ownerRole: 'President', ownerName: 'Dave' };
    const id = generateAgentId(fd);
    expect(id).toMatch(/^president-dave-[a-f0-9]{4}$/);
  });

  it('caches on formData so subsequent calls return the same id', () => {
    const fd = { ownerRole: 'President', ownerName: 'Dave' };
    const id1 = generateAgentId(fd);
    const id2 = generateAgentId(fd);
    expect(id1).toBe(id2);
  });

  it('handles roles with slashes', () => {
    const fd = { ownerRole: 'Secretary/Treasurer', ownerName: 'Jane' };
    const id = generateAgentId(fd);
    expect(id).toMatch(/^secretary-treasurer-jane-[a-f0-9]{4}$/);
  });

  it('handles blank role and name gracefully', () => {
    const fd = { ownerRole: '', ownerName: '' };
    const id = generateAgentId(fd);
    expect(id).toMatch(/^staff-unknown-[a-f0-9]{4}$/);
  });
});

describe('mapEnergyPattern', () => {
  it.each([
    ['Morning', 'morning'],
    ['I peak in the morning', 'morning'],
    ['Mid-morning', 'mid-morning'],
    ['Afternoon', 'afternoon'],
    ['Evening', 'evening'],
    ['It varies', 'variable'],
    ['', 'variable'],
  ])('maps "%s" to "%s"', (input, expected) => {
    expect(mapEnergyPattern(input)).toBe(expected);
  });
});

describe('mapFocusStyle', () => {
  it.each([
    ['Deep blocks of uninterrupted time', 'deep_blocks'],
    ['Pomodoro-style intervals', 'pomodoro'],
    ['25 min timer sessions', 'pomodoro'],
    ['Go with the flow', 'flow_based'],
    ['', 'flow_based'],
  ])('maps "%s" to "%s"', (input, expected) => {
    expect(mapFocusStyle(input)).toBe(expected);
  });
});

describe('mapInfoFormat', () => {
  it.each([
    ['Bullet points', 'bullets'],
    ['Prose / paragraphs', 'prose'],
    ['Tables and comparisons', 'tables'],
    ['Mix of all', 'mixed'],
    ['', 'mixed'],
  ])('maps "%s" to "%s"', (input, expected) => {
    expect(mapInfoFormat(input)).toBe(expected);
  });
});

describe('parsePronouns', () => {
  it.each([
    ['he/him', { subject: 'he', object: 'him', possessive: 'his' }],
    ['he/him/his', { subject: 'he', object: 'him', possessive: 'his' }],
    ['she/her', { subject: 'she', object: 'her', possessive: 'her' }],
    ['she/her/hers', { subject: 'she', object: 'her', possessive: 'her' }],
    ['they/them', { subject: 'they', object: 'them', possessive: 'their' }],
    ['', { subject: 'they', object: 'them', possessive: 'their' }],
    ['ze/zir', { subject: 'they', object: 'them', possessive: 'their' }],
    [null, { subject: 'they', object: 'them', possessive: 'their' }],
  ])('parses "%s" correctly', (input, expected) => {
    expect(parsePronouns(input)).toEqual(expected);
  });
});

describe('deriveValues', () => {
  it('returns 3-5 values', () => {
    const vals = deriveValues({
      vibeSelection: 'Calm and supportive',
      communicationStyle: 'Brief and direct',
      badNewsApproach: 'Straight and direct',
    });
    expect(vals.length).toBeGreaterThanOrEqual(3);
    expect(vals.length).toBeLessThanOrEqual(5);
  });

  it('always includes solidarity value', () => {
    const vals = deriveValues({});
    expect(vals[0]).toBe('Solidarity with workers');
  });
});

describe('buildFrontmatter', () => {
  it('produces valid YAML-style frontmatter', () => {
    const fm = buildFrontmatter({ version: '1.0', agent_id: 'test-abc-1234' });
    expect(fm).toContain('---');
    expect(fm).toContain('version: "1.0"');
    expect(fm).toContain('agent_id: "test-abc-1234"');
  });

  it('renders arrays as YAML lists', () => {
    const fm = buildFrontmatter({ traits: ['a', 'b'] });
    expect(fm).toContain('traits:');
    expect(fm).toContain('  - "a"');
    expect(fm).toContain('  - "b"');
  });
});

describe('splitTimeSinks', () => {
  it('splits by newlines', () => {
    expect(splitTimeSinks('Email\nMeetings\nReports')).toEqual(['Email', 'Meetings', 'Reports']);
  });

  it('splits by semicolons', () => {
    expect(splitTimeSinks('Email; Meetings; Reports')).toEqual(['Email', 'Meetings', 'Reports']);
  });

  it('handles empty/null', () => {
    expect(splitTimeSinks('')).toEqual([]);
    expect(splitTimeSinks(null)).toEqual([]);
  });
});
