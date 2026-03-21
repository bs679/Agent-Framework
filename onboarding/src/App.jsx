import React, { useState } from 'react';
import JSZip from 'jszip';
import { generateAll, generateAgentId } from './generators/index.js';

const VIBE_OPTIONS = [
  'Calm and supportive',
  'Focused and efficient',
  'Warm and collaborative',
  'Adaptive',
];

const OVERWHELM_OPTIONS = [
  'Too many meetings',
  'Email overload',
  'Unclear priorities',
  'Last-minute requests',
  'Context switching',
  'Information scattered across systems',
];

const ROLE_OPTIONS = [
  'President',
  'Secretary/Treasurer',
  'Executive Secretary',
  'Staff',
];

const INITIAL_FORM = {
  ownerName: '',            // Q1
  ownerRole: '',            // Q2
  pronouns: '',             // Q3
  energyPattern: '',        // Q4
  focusStyle: '',           // Q5
  overwhelmTriggers: [],    // Q6
  communicationStyle: '',   // Q7
  informationFormat: '',    // Q8
  badNewsApproach: '',      // Q9
  agentName: '',            // Q10
  vibeSelection: '',        // Q11
  rememberThis: '',         // Q12
  currentTimeSinks: '',     // Q17
  neverDoThis: '',          // Q18
};

const DRAFT_KEY = 'chca-onboarding-draft';

// Fields that generators require for well-formed output.
const REQUIRED_FIELDS = [
  { key: 'ownerName',          label: 'Your name (Q1)' },
  { key: 'ownerRole',          label: 'Your role (Q2)' },
  { key: 'pronouns',           label: 'Your pronouns (Q3)' },
  { key: 'energyPattern',      label: 'Energy pattern (Q4)' },
  { key: 'focusStyle',         label: 'Focus style (Q5)' },
  { key: 'communicationStyle', label: 'Communication style (Q7)' },
  { key: 'informationFormat',  label: 'Information format (Q8)' },
  { key: 'badNewsApproach',    label: 'Bad-news approach (Q9)' },
  { key: 'vibeSelection',      label: 'Agent vibe (Q11)' },
];

function validateForm(form) {
  const missing = REQUIRED_FIELDS.filter(({ key }) => {
    const v = form[key];
    return !v || (typeof v === 'string' && !v.trim());
  });
  return missing.map(({ label }) => label);
}

export default function App() {
  const [form, setForm] = useState(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      return saved ? { ...INITIAL_FORM, ...JSON.parse(saved) } : INITIAL_FORM;
    } catch {
      return INITIAL_FORM;
    }
  });
  const [generated, setGenerated] = useState(null);
  const [error, setError] = useState('');
  const [draftSaved, setDraftSaved] = useState(false);

  function update(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  function toggleOverwhelm(value) {
    setForm((prev) => {
      const triggers = prev.overwhelmTriggers.includes(value)
        ? prev.overwhelmTriggers.filter((t) => t !== value)
        : [...prev.overwhelmTriggers, value];
      return { ...prev, overwhelmTriggers: triggers };
    });
  }

  function handleSaveDraft() {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
      setDraftSaved(true);
      setTimeout(() => setDraftSaved(false), 2000);
    } catch {
      // localStorage not available — silently ignore
    }
  }

  function handleClearDraft() {
    localStorage.removeItem(DRAFT_KEY);
    setForm(INITIAL_FORM);
    setGenerated(null);
    setError('');
  }

  async function handleGenerate() {
    setError('');
    const missing = validateForm(form);
    if (missing.length > 0) {
      setError(`Please complete the following required fields: ${missing.join(', ')}.`);
      return;
    }

    const files = generateAll({ ...form });
    setGenerated(files);
  }

  async function handleDownload() {
    if (!generated) return;

    const zip = new JSZip();
    const agentId = Object.values(generated)[0]
      .match(/agent_id:\s*"([^"]+)"/)?.[1] || 'agent';

    const folder = zip.folder(agentId);
    for (const [filename, content] of Object.entries(generated)) {
      folder.file(filename, content);
    }

    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${agentId}-config.zip`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ maxWidth: 700, margin: '2rem auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>CHCA Agent Onboarding</h1>
      <p>Complete this form to generate your AI agent's configuration files.</p>

      <fieldset>
        <legend>About You</legend>
        <label>Q1 — Your name<br />
          <input value={form.ownerName} onChange={update('ownerName')} placeholder="Dave" />
        </label><br />

        <label>Q2 — Your role<br />
          <select value={form.ownerRole} onChange={update('ownerRole')}>
            <option value="">Select…</option>
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label><br />

        <label>Q3 — Your pronouns<br />
          <input value={form.pronouns} onChange={update('pronouns')} placeholder="he/him, she/her, they/them" />
        </label>
      </fieldset>

      <fieldset>
        <legend>Your Work Style</legend>
        <label>Q4 — When do you have the most energy?<br />
          <select value={form.energyPattern} onChange={update('energyPattern')}>
            <option value="">Select…</option>
            <option value="Morning">Morning</option>
            <option value="Mid-morning">Mid-morning</option>
            <option value="Afternoon">Afternoon</option>
            <option value="Evening">Evening</option>
            <option value="It varies">It varies</option>
          </select>
        </label><br />

        <label>Q5 — How do you prefer to focus?<br />
          <select value={form.focusStyle} onChange={update('focusStyle')}>
            <option value="">Select…</option>
            <option value="Deep blocks of uninterrupted time">Deep blocks of uninterrupted time</option>
            <option value="Pomodoro-style intervals">Pomodoro-style intervals</option>
            <option value="Go with the flow">Go with the flow</option>
          </select>
        </label><br />

        <label>Q6 — What overwhelms you? (select all that apply)</label><br />
        {OVERWHELM_OPTIONS.map((opt) => (
          <label key={opt} style={{ display: 'block', marginLeft: '1rem' }}>
            <input
              type="checkbox"
              checked={form.overwhelmTriggers.includes(opt)}
              onChange={() => toggleOverwhelm(opt)}
            />{' '}{opt}
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>Communication</legend>
        <label>Q7 — How should your agent communicate?<br />
          <select value={form.communicationStyle} onChange={update('communicationStyle')}>
            <option value="">Select…</option>
            <option value="Brief and direct">Brief and direct</option>
            <option value="Detailed and thorough">Detailed and thorough</option>
            <option value="Casual and conversational">Casual and conversational</option>
            <option value="Formal and precise">Formal and precise</option>
          </select>
        </label><br />

        <label>Q8 — How do you prefer information formatted?<br />
          <select value={form.informationFormat} onChange={update('informationFormat')}>
            <option value="">Select…</option>
            <option value="Bullet points">Bullet points</option>
            <option value="Prose / paragraphs">Prose / paragraphs</option>
            <option value="Tables and comparisons">Tables and comparisons</option>
            <option value="Mix of all">Mix of all</option>
          </select>
        </label><br />

        <label>Q9 — How should your agent deliver bad news?<br />
          <select value={form.badNewsApproach} onChange={update('badNewsApproach')}>
            <option value="">Select…</option>
            <option value="Straight and direct">Straight and direct</option>
            <option value="Gently, with context first">Gently, with context first</option>
            <option value="Lead with options and solutions">Lead with options and solutions</option>
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>Your Agent</legend>
        <label>Q10 — Name your agent (leave blank to let it choose)<br />
          <input value={form.agentName} onChange={update('agentName')} placeholder="Optional" />
        </label><br />

        <label>Q11 — What vibe should your agent have?<br />
          <select value={form.vibeSelection} onChange={update('vibeSelection')}>
            <option value="">Select…</option>
            {VIBE_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>Context</legend>
        <label>Q12 — Anything you want your agent to always remember?<br />
          <textarea
            value={form.rememberThis}
            onChange={update('rememberThis')}
            rows={3}
            style={{ width: '100%' }}
            placeholder="Optional — your agent will keep this in mind at all times"
          />
        </label><br />

        <label>Q17 — What tasks eat up too much of your time right now?<br />
          <textarea
            value={form.currentTimeSinks}
            onChange={update('currentTimeSinks')}
            rows={3}
            style={{ width: '100%' }}
            placeholder="One per line, or write freely"
          />
        </label><br />

        <label>Q18 — What should your agent never do?<br />
          <textarea
            value={form.neverDoThis}
            onChange={update('neverDoThis')}
            rows={3}
            style={{ width: '100%' }}
            placeholder="Optional — hard boundaries for your agent"
          />
        </label>
      </fieldset>

      {error && <p style={{ color: '#d97706' }}>{error}</p>}

      <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <button onClick={handleGenerate}>Generate Config Files</button>
        {generated && <button onClick={handleDownload}>Download ZIP</button>}
        <button onClick={handleSaveDraft} style={{ marginLeft: 'auto' }}>
          {draftSaved ? 'Saved ✓' : 'Save Draft'}
        </button>
        <button onClick={handleClearDraft} style={{ color: '#888' }}>
          Clear Draft
        </button>
      </div>

      {generated && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Generated Files</h2>
          {Object.entries(generated).map(([name, content]) => (
            <details key={name} style={{ marginBottom: '1rem' }}>
              <summary><strong>{name}</strong></summary>
              <pre style={{
                background: '#1a1a1a',
                color: '#e0e0e0',
                padding: '1rem',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.85rem',
              }}>{content}</pre>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
