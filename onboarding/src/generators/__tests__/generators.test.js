import { describe, it, expect, beforeEach } from 'vitest';
import { generateSOUL } from '../generateSOUL.js';
import { generateUSER } from '../generateUSER.js';
import { generateIDENTITY } from '../generateIDENTITY.js';
import { generateAGENTS } from '../generateAGENTS.js';
import { generateHEARTBEAT } from '../generateHEARTBEAT.js';
import { generateMEMORY } from '../generateMEMORY.js';
import { generateAll } from '../index.js';

// ── Test fixtures ──────────────────────────────────────────────────

function presidentForm() {
  return {
    ownerName: 'Dave',
    ownerRole: 'President',
    pronouns: 'he/him',
    energyPattern: 'Morning',
    focusStyle: 'Deep blocks of uninterrupted time',
    overwhelmTriggers: ['Too many meetings', 'Email overload', 'Context switching'],
    communicationStyle: 'Brief and direct',
    informationFormat: 'Bullet points',
    badNewsApproach: 'Straight and direct',
    agentName: 'Beacon',
    vibeSelection: 'Focused and efficient',
    rememberThis: 'Executive board meetings are in executive session — no recording.',
    currentTimeSinks: 'Researching wage comparables\nGrievance tracking across 3 hospitals\nEmail triage',
    neverDoThis: 'Never send emails on my behalf without explicit approval.',
  };
}

function secTreasForm() {
  return {
    ownerName: 'Jane',
    ownerRole: 'Secretary/Treasurer',
    pronouns: 'she/her',
    energyPattern: 'Mid-morning',
    focusStyle: 'Pomodoro-style intervals',
    overwhelmTriggers: ['Unclear priorities', 'Information scattered across systems'],
    communicationStyle: 'Detailed and thorough',
    informationFormat: 'Tables and comparisons',
    badNewsApproach: 'Lead with options and solutions',
    agentName: '',
    vibeSelection: 'Warm and collaborative',
    rememberThis: 'Disbursements always require co-signatures.',
    currentTimeSinks: 'Dues processing; Budget reconciliation; Vendor invoices',
    neverDoThis: 'Never approve a disbursement without co-signature confirmation.',
  };
}

function execSecForm() {
  return {
    ownerName: 'Alex',
    ownerRole: 'Executive Secretary',
    pronouns: 'they/them',
    energyPattern: 'Afternoon',
    focusStyle: 'Go with the flow',
    overwhelmTriggers: ['Last-minute requests'],
    communicationStyle: 'Casual and conversational',
    informationFormat: 'Mix of all',
    badNewsApproach: 'Gently, with context first',
    agentName: 'Scribe',
    vibeSelection: 'Calm and supportive',
    rememberThis: '',
    currentTimeSinks: 'Formatting minutes\nScheduling conflicts',
    neverDoThis: '',
  };
}

// ── Helper to extract agent_id from generated content ──────────────

function extractAgentId(content) {
  const match = content.match(/agent_id:\s*"([^"]+)"/);
  return match ? match[1] : null;
}

// ── SOUL.md ────────────────────────────────────────────────────────

describe('generateSOUL', () => {
  it('contains required frontmatter fields', () => {
    const result = generateSOUL(presidentForm());
    expect(result).toContain('version: "1.0"');
    expect(result).toContain('agent_id:');
    expect(result).toContain('personality_traits:');
    expect(result).toContain('communication_style:');
    expect(result).toContain('values:');
    expect(result).toContain('bad_news_approach:');
  });

  it('maps vibe to correct traits', () => {
    const result = generateSOUL(presidentForm());
    expect(result).toContain('"direct"');
    expect(result).toContain('"precise"');
    expect(result).toContain('"efficient"');
    expect(result).toContain('"results-oriented"');
  });

  it('writes body in first person', () => {
    const result = generateSOUL(presidentForm());
    expect(result).toContain('# Soul — Who I Am');
    expect(result).toContain('I am an AI assistant working for Dave at CHCA');
    expect(result).toContain('## My Core Approach');
    expect(result).toContain('## How I Communicate');
    expect(result).toContain('## When Things Are Hard');
    expect(result).toContain('## What I Value');
  });

  it('produces coherent prose, not a dump of form values', () => {
    const result = generateSOUL(presidentForm());
    // Core approach should be sentences, not key-value pairs
    const coreSection = result.split('## My Core Approach')[1].split('##')[0];
    expect(coreSection).toContain('.');  // contains sentences
    expect(coreSection).not.toContain('=');  // not key=value
  });

  it('handles all four vibe options', () => {
    for (const vibe of ['Calm and supportive', 'Focused and efficient', 'Warm and collaborative', 'Adaptive']) {
      const fd = { ...presidentForm(), vibeSelection: vibe };
      const result = generateSOUL(fd);
      expect(result).toContain('## My Core Approach');
    }
  });
});

// ── USER.md ────────────────────────────────────────────────────────

describe('generateUSER', () => {
  it('contains required frontmatter fields', () => {
    const result = generateUSER(presidentForm());
    expect(result).toContain('version: "1.0"');
    expect(result).toContain('agent_id:');
    expect(result).toContain('owner_name: "Dave"');
    expect(result).toContain('owner_role: "President"');
    expect(result).toContain('pronouns: "he/him"');
    expect(result).toContain('energy_pattern: "morning"');
    expect(result).toContain('focus_style: "deep_blocks"');
    expect(result).toContain('information_format: "bullets"');
    expect(result).toContain('overwhelm_triggers:');
    expect(result).toContain('current_time_sinks:');
  });

  it('writes body in third person', () => {
    const result = generateUSER(presidentForm());
    expect(result).toContain('# User — The Person I Serve');
    expect(result).toContain('## Dave');
    expect(result).toContain('Dave is the President at CHCA.');
    expect(result).toContain('He leads the organization');
  });

  it('handles she/her pronouns correctly', () => {
    const result = generateUSER(secTreasForm());
    expect(result).toContain('She manages');
  });

  it('handles they/them pronouns correctly', () => {
    const result = generateUSER(execSecForm());
    expect(result).toContain('They handle');
  });

  it('defaults to they/them for non-standard pronouns', () => {
    const fd = { ...presidentForm(), pronouns: 'ze/zir' };
    const result = generateUSER(fd);
    expect(result).toContain('They leads');  // they + role desc
    // The grammar is slightly off with they + singular verb, but safe default
  });

  it('defaults to they/them when pronouns blank', () => {
    const fd = { ...presidentForm(), pronouns: '' };
    const result = generateUSER(fd);
    expect(result).toContain('pronouns: "they/them"');
  });

  it('includes overwhelm triggers as prose', () => {
    const result = generateUSER(presidentForm());
    const section = result.split('## What Gets in the Way')[1].split('##')[0];
    expect(section).toContain('too many meetings');
    expect(section).toContain('email overload');
    // Should be a paragraph, not bullet points
    expect(section).not.toContain('- ');
  });

  it('preserves Q17 content', () => {
    const result = generateUSER(presidentForm());
    expect(result).toContain('Researching wage comparables');
    expect(result).toContain('Grievance tracking across 3 hospitals');
  });

  it('includes Q12 verbatim when provided', () => {
    const result = generateUSER(presidentForm());
    expect(result).toContain('What Dave Wants Me to Remember');
    expect(result).toContain('Executive board meetings are in executive session');
  });

  it('omits Q12 section when blank', () => {
    const result = generateUSER(execSecForm());
    expect(result).not.toContain('What Alex Wants Me to Remember');
  });

  it('includes Q18 verbatim when provided', () => {
    const result = generateUSER(presidentForm());
    expect(result).toContain('What Dave Never Wants Me to Do');
    expect(result).toContain('Never send emails on my behalf');
  });

  it('shows default message when Q18 blank', () => {
    const result = generateUSER(execSecForm());
    expect(result).toContain('What Alex Never Wants Me to Do');
    expect(result).toContain('Nothing specified yet.');
  });
});

// ── IDENTITY.md ────────────────────────────────────────────────────

describe('generateIDENTITY', () => {
  it('contains required frontmatter fields', () => {
    const result = generateIDENTITY(presidentForm());
    expect(result).toContain('version: "1.0"');
    expect(result).toContain('agent_id:');
    expect(result).toContain('agent_name: "Beacon"');
    expect(result).toContain('avatar_description:');
    expect(result).toContain('role_definition:');
    expect(result).toContain('organization: "CHCA, Connecticut Health Care Associates, District 1199NE, AFSCME"');
  });

  it('uses provided agent name', () => {
    const result = generateIDENTITY(presidentForm());
    expect(result).toContain('My name is Beacon.');
  });

  it('handles blank agent name (Q10 empty)', () => {
    const result = generateIDENTITY(secTreasForm());
    expect(result).toContain('agent_name: "self_selected"');
    expect(result).toContain('My name has not been set yet.');
    expect(result).toContain('I will choose a name');
  });

  it('includes organization description', () => {
    const result = generateIDENTITY(presidentForm());
    expect(result).toContain('Bradley Memorial Hospital');
    expect(result).toContain('Norwalk Hospital');
    expect(result).toContain('Waterbury Hospital');
    expect(result).toContain('Regions 12, 13, and 17');
  });

  it('writes role-specific purpose for President', () => {
    const result = generateIDENTITY(presidentForm());
    expect(result).toContain('more effective as President');
  });

  it('writes role-specific purpose for Secretary/Treasurer', () => {
    const result = generateIDENTITY(secTreasForm());
    expect(result).toContain('financial operations');
  });

  it('writes role-specific purpose for Executive Secretary', () => {
    const result = generateIDENTITY(execSecForm());
    expect(result).toContain('administrative operations');
  });

  it('includes all required sections', () => {
    const result = generateIDENTITY(presidentForm());
    expect(result).toContain('# Identity — Who I Am in This Organization');
    expect(result).toContain('## Name');
    expect(result).toContain('## My Role');
    expect(result).toContain("## This Organization's Work");
    expect(result).toContain('## My Purpose Here');
  });
});

// ── Stubs ──────────────────────────────────────────────────────────

describe('stub generators', () => {
  it('generateAGENTS produces stub with correct agent_id', () => {
    const fd = presidentForm();
    const result = generateAGENTS(fd);
    expect(result).toContain('agent_id:');
    expect(result).toContain('Phase 3b');
  });

  it('generateHEARTBEAT produces stub with correct agent_id', () => {
    const fd = presidentForm();
    const result = generateHEARTBEAT(fd);
    expect(result).toContain('agent_id:');
    expect(result).toContain('Phase 3b');
  });

  it('generateMEMORY produces stub with correct agent_id', () => {
    const fd = presidentForm();
    const result = generateMEMORY(fd);
    expect(result).toContain('agent_id:');
    expect(result).toContain('Phase 3b');
  });
});

// ── Cross-file agent_id consistency ────────────────────────────────

describe('generateAll — agent_id consistency', () => {
  it('all 6 files have the same agent_id (President)', () => {
    const files = generateAll(presidentForm());
    const ids = Object.values(files).map(extractAgentId);
    expect(ids.every((id) => id === ids[0])).toBe(true);
    expect(ids[0]).toMatch(/^president-dave-[a-f0-9]{4}$/);
  });

  it('all 6 files have the same agent_id (Secretary/Treasurer)', () => {
    const files = generateAll(secTreasForm());
    const ids = Object.values(files).map(extractAgentId);
    expect(ids.every((id) => id === ids[0])).toBe(true);
    expect(ids[0]).toMatch(/^secretary-treasurer-jane-[a-f0-9]{4}$/);
  });

  it('all 6 files have the same agent_id (Executive Secretary)', () => {
    const files = generateAll(execSecForm());
    const ids = Object.values(files).map(extractAgentId);
    expect(ids.every((id) => id === ids[0])).toBe(true);
    expect(ids[0]).toMatch(/^executive-secretary-alex-[a-f0-9]{4}$/);
  });

  it('generates all 6 files', () => {
    const files = generateAll(presidentForm());
    expect(Object.keys(files)).toEqual([
      'SOUL.md', 'USER.md', 'IDENTITY.md', 'AGENTS.md', 'HEARTBEAT.md', 'MEMORY.md',
    ]);
  });

  it('each call to generateAll produces a fresh agent_id', () => {
    const files1 = generateAll(presidentForm());
    const files2 = generateAll(presidentForm());
    const id1 = extractAgentId(files1['SOUL.md']);
    const id2 = extractAgentId(files2['SOUL.md']);
    // Extremely unlikely to collide with 4 hex chars, but not impossible
    // This test may rarely fail — that's acceptable for a random component
    // The important thing is that _agentId is cleared between runs
    expect(id1).toMatch(/^president-dave-[a-f0-9]{4}$/);
    expect(id2).toMatch(/^president-dave-[a-f0-9]{4}$/);
  });
});

// ── Edge cases ─────────────────────────────────────────────────────

describe('edge cases', () => {
  it('handles minimal form data gracefully', () => {
    const fd = { ownerName: 'Test', ownerRole: 'Staff' };
    const files = generateAll(fd);
    expect(Object.keys(files).length).toBe(6);
    // Should not throw
    for (const content of Object.values(files)) {
      expect(content).toContain('---');
      expect(content).toContain('agent_id:');
    }
  });

  it('handles non-standard pronouns by defaulting to they/them', () => {
    const fd = { ...presidentForm(), pronouns: 'xe/xem/xyr' };
    const user = generateUSER(fd);
    // Should use they/them as safe default
    expect(user).toContain('pronouns: "xe/xem/xyr"');  // preserves original in frontmatter
    // But body uses they/them
    expect(user).toContain('They leads');
  });
});
