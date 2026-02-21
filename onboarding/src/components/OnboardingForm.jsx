import React, { useState } from 'react';
import { buildConfigZip } from '../generators/buildZip.js';

const ROLE_OPTIONS = [
  'President',
  'Secretary/Treasurer',
  'Executive Secretary',
  'Staff',
];

const ENERGY_OPTIONS = [
  'Early morning',
  'Mid-morning',
  'Afternoon',
  'Evening',
  'It varies',
];

const TONE_OPTIONS = [
  'Calm and direct',
  'Warm and supportive',
  'Professional and concise',
  'Casual and friendly',
];

const FORMAT_OPTIONS = [
  'Bullet points',
  'Short paragraphs',
  'Detailed narrative',
  'Just the essentials',
];

const BAD_NEWS_OPTIONS = [
  'Lead with the facts, then offer options',
  'Soften it first, then give me the details',
  'Be blunt — just tell me',
  'Ask me if now is a good time first',
];

const PERSONALITY_OPTIONS = [
  'Steady and methodical',
  'Warm and encouraging',
  'Crisp and efficient',
  'Curious and proactive',
];

const PREP_TIMING_OPTIONS = [
  '15 minutes before',
  '1 hour before',
  'Morning of the meeting',
  'Day before',
];

const NOTE_STYLE_OPTIONS = [
  'Key decisions and action items only',
  'Detailed minutes',
  'Bullet summary after the meeting',
  'I handle my own notes',
];

const INITIAL_FORM = {
  ownerName: '',
  ownerRole: 'President',
  ownerPronouns: '',
  energyPattern: 'It varies',
  focusPreferences: '',
  overwhelmTriggers: '',
  communicationTone: 'Calm and direct',
  communicationFormat: 'Bullet points',
  badNewsDelivery: 'Lead with the facts, then offer options',
  agentName: '',
  agentPersonality: 'Steady and methodical',
  meetingPrepTiming: '1 hour before',
  noteCaptureStyle: 'Key decisions and action items only',
  currentTimeSinks: '',
};

export function OnboardingForm() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [status, setStatus] = useState(null);

  function update(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function handleGenerate(e) {
    e.preventDefault();

    if (!form.ownerName.trim()) {
      setStatus({ type: 'error', message: 'Name is required.' });
      return;
    }

    try {
      setStatus({ type: 'success', message: 'Generating config files...' });
      const { blob, filename } = await buildConfigZip(form);

      // Trigger download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setStatus({
        type: 'success',
        message: `Downloaded ${filename} — 6 config files + README.txt`,
      });
    } catch (err) {
      setStatus({ type: 'error', message: `Generation failed: ${err.message}` });
    }
  }

  return (
    <form onSubmit={handleGenerate}>
      <h1>CHCA Agent Onboarding</h1>
      <p className="subtitle">
        Configure your personal AI agent. All 6 config files will be generated
        as a single ZIP download.
      </p>

      {/* Section 1: About You */}
      <div className="section">
        <h2>1. About You</h2>
        <label htmlFor="ownerName">Your name *</label>
        <input
          id="ownerName"
          type="text"
          value={form.ownerName}
          onChange={update('ownerName')}
          placeholder="e.g. Dave"
          required
        />
        <label htmlFor="ownerRole">Your role</label>
        <select id="ownerRole" value={form.ownerRole} onChange={update('ownerRole')}>
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <label htmlFor="ownerPronouns">Pronouns (optional)</label>
        <input
          id="ownerPronouns"
          type="text"
          value={form.ownerPronouns}
          onChange={update('ownerPronouns')}
          placeholder="e.g. he/him, she/her, they/them"
        />
      </div>

      {/* Section 2: Your Work Style */}
      <div className="section">
        <h2>2. Your Work Style</h2>
        <label htmlFor="energyPattern">When do you have the most energy?</label>
        <select id="energyPattern" value={form.energyPattern} onChange={update('energyPattern')}>
          {ENERGY_OPTIONS.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <label htmlFor="focusPreferences">Focus preferences (optional)</label>
        <input
          id="focusPreferences"
          type="text"
          value={form.focusPreferences}
          onChange={update('focusPreferences')}
          placeholder="e.g. No interruptions before 10am"
        />
        <label htmlFor="overwhelmTriggers">What triggers overwhelm? (optional)</label>
        <textarea
          id="overwhelmTriggers"
          value={form.overwhelmTriggers}
          onChange={update('overwhelmTriggers')}
          placeholder="e.g. Too many unread emails, back-to-back meetings"
        />
      </div>

      {/* Section 3: Communication */}
      <div className="section">
        <h2>3. Communication</h2>
        <label htmlFor="communicationTone">Preferred tone</label>
        <select id="communicationTone" value={form.communicationTone} onChange={update('communicationTone')}>
          {TONE_OPTIONS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <label htmlFor="communicationFormat">Preferred format</label>
        <select id="communicationFormat" value={form.communicationFormat} onChange={update('communicationFormat')}>
          {FORMAT_OPTIONS.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
        <label htmlFor="badNewsDelivery">How should I deliver bad news?</label>
        <select id="badNewsDelivery" value={form.badNewsDelivery} onChange={update('badNewsDelivery')}>
          {BAD_NEWS_OPTIONS.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </div>

      {/* Section 4: Your Agent */}
      <div className="section">
        <h2>4. Your Agent</h2>
        <label htmlFor="agentName">Agent name (optional — leave blank for self-selection)</label>
        <input
          id="agentName"
          type="text"
          value={form.agentName}
          onChange={update('agentName')}
          placeholder="Leave blank and the agent picks its own name"
        />
        <label htmlFor="agentPersonality">Agent personality</label>
        <select id="agentPersonality" value={form.agentPersonality} onChange={update('agentPersonality')}>
          {PERSONALITY_OPTIONS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Section 5: Meetings */}
      <div className="section">
        <h2>5. Meetings</h2>
        <label htmlFor="meetingPrepTiming">When should I prep you for meetings?</label>
        <select id="meetingPrepTiming" value={form.meetingPrepTiming} onChange={update('meetingPrepTiming')}>
          {PREP_TIMING_OPTIONS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <label htmlFor="noteCaptureStyle">Note capture style</label>
        <select id="noteCaptureStyle" value={form.noteCaptureStyle} onChange={update('noteCaptureStyle')}>
          {NOTE_STYLE_OPTIONS.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>

      {/* Section 6: Information */}
      {/* (delivery preferences are in Communication section above) */}

      {/* Section 7: Context */}
      <div className="section">
        <h2>6. Current Context</h2>
        <label htmlFor="currentTimeSinks">
          What's eating up your time right now? (seeds initial agent memory)
        </label>
        <textarea
          id="currentTimeSinks"
          value={form.currentTimeSinks}
          onChange={update('currentTimeSinks')}
          placeholder="e.g. Preparing for contract negotiations, catching up on grievance backlog"
          rows={4}
        />
      </div>

      <button type="submit" className="btn">
        Generate Config Files
      </button>

      {status && (
        <div className={`status ${status.type}`}>{status.message}</div>
      )}
    </form>
  );
}
