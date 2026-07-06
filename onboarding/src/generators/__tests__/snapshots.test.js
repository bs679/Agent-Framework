import { describe, it, expect } from 'vitest';
import { generateAll } from '../index.js';

// ── Golden-file snapshot tests ──────────────────────────────────────
//
// One complete, realistic fixture per role class (President,
// Secretary/Treasurer, Staff). Every select-style field uses an exact
// option value from App.jsx (the source of truth for valid values).
//
// Determinism: generateAgentId appends a random 4-char hex suffix
// (utils.js randomHex4), and generateAll clears any cached _agentId
// before running, so the id cannot be pinned via the API. Instead we
// extract the generated agent id from the output and replace every
// occurrence with a stable placeholder ({role}-{name}-xxxx) before
// snapshotting. No generator embeds dates/timestamps, so nothing else
// needs normalizing.

// ── Fixtures ───────────────────────────────────────────────────────

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
    rememberThis: 'Executive board meetings are in executive session — no recording. Contract negotiations with Waterbury Hospital resume in September.',
    currentTimeSinks: 'Researching wage comparables across CT hospitals\nGrievance tracking across 3 hospitals\nEmail triage every morning',
    neverDoThis: 'Never send emails on my behalf without explicit approval. Never share member information outside the union.',
  };
}

function secretaryTreasurerForm() {
  return {
    ownerName: 'Maria',
    ownerRole: 'Secretary/Treasurer',
    pronouns: 'she/her',
    energyPattern: 'Mid-morning',
    focusStyle: 'Pomodoro-style intervals',
    overwhelmTriggers: ['Unclear priorities', 'Information scattered across systems'],
    communicationStyle: 'Detailed and thorough',
    informationFormat: 'Tables and comparisons',
    badNewsApproach: 'Lead with options and solutions',
    agentName: 'Ledger',
    vibeSelection: 'Warm and collaborative',
    rememberThis: 'All disbursements require co-signatures. Quarterly LM-2 filings are due to the Department of Labor.',
    currentTimeSinks: 'Dues processing and reconciliation; Budget reports for the executive board; Chasing vendor invoices',
    neverDoThis: 'Never approve or suggest approving a disbursement without co-signature confirmation.',
  };
}

function staffForm() {
  return {
    ownerName: 'Jordan',
    ownerRole: 'Staff',
    pronouns: 'they/them',
    energyPattern: 'Afternoon',
    focusStyle: 'Go with the flow',
    overwhelmTriggers: ['Last-minute requests', 'Context switching'],
    communicationStyle: 'Casual and conversational',
    informationFormat: 'Mix of all',
    badNewsApproach: 'Gently, with context first',
    agentName: '',
    vibeSelection: 'Calm and supportive',
    rememberThis: 'Member calls always take priority over paperwork.',
    currentTimeSinks: 'Formatting meeting minutes\nJuggling scheduling conflicts\nData entry into the member database',
    neverDoThis: 'Never contact members directly without checking with me first.',
  };
}

const FIXTURES = [
  ['President', presidentForm],
  ['Secretary/Treasurer', secretaryTreasurerForm],
  ['Staff', staffForm],
];

const FILE_NAMES = ['SOUL.md', 'USER.md', 'IDENTITY.md', 'AGENTS.md', 'HEARTBEAT.md', 'MEMORY.md'];

// ── Normalization helpers ──────────────────────────────────────────

function extractAgentId(content) {
  const match = content.match(/agent_id:\s*"([^"]+)"/);
  return match ? match[1] : null;
}

/**
 * Replace every occurrence of the run's random agent id with a stable
 * placeholder so snapshots do not churn between runs.
 * e.g. "president-dave-a3f2" → "president-dave-xxxx"
 */
function normalize(content, agentId) {
  const placeholder = agentId.replace(/-[a-f0-9]{4}$/, '-xxxx');
  return content.split(agentId).join(placeholder);
}

function generateNormalized(formData) {
  const files = generateAll(formData);
  const agentId = extractAgentId(files['SOUL.md']);
  expect(agentId).toMatch(/^[a-z0-9-]+-[a-f0-9]{4}$/);
  const normalized = {};
  for (const [name, content] of Object.entries(files)) {
    normalized[name] = normalize(content, agentId);
  }
  return normalized;
}

// ── Snapshots: 3 roles × 6 files = 18 ──────────────────────────────

for (const [roleLabel, makeForm] of FIXTURES) {
  describe(`golden files — ${roleLabel}`, () => {
    const files = generateNormalized(makeForm());

    for (const fileName of FILE_NAMES) {
      it(`${fileName} matches snapshot`, () => {
        expect(files[fileName]).toMatchSnapshot();
      });
    }

    it('every file starts with YAML frontmatter containing agent_id and version', () => {
      for (const fileName of FILE_NAMES) {
        const content = files[fileName];
        expect(content.startsWith('---\n')).toBe(true);
        const closing = content.indexOf('\n---', 4);
        expect(closing).toBeGreaterThan(0);
        const frontmatter = content.slice(0, closing + 4);
        expect(frontmatter).toMatch(/^agent_id:\s*"/m);
        expect(frontmatter).toMatch(/^version:\s*"/m);
      }
    });
  });
}
