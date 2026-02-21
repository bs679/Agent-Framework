import { useState } from 'react'
import JSZip from 'jszip'
import { generateAllConfigs } from '../generators/configGenerators'

const SECTION_LABELS = [
  'About You',
  'Your Work Style',
  'Communication',
  'Your Agent',
  'Meetings',
  'Information Flow',
  'Getting Started',
]

const FIELD_LABELS = {
  name: 'Your name',
  role: 'Your role',
  pronouns: 'Your pronouns',
  bestThinkingTime: 'Best thinking time',
  focusStyle: 'How you prefer to focus',
  derailTriggers: 'What tends to derail you',
  communicationStyle: 'How your assistant communicates',
  infoDelivery: 'How information is delivered',
  difficultNews: 'When there\'s difficult news',
  agentName: 'Assistant name',
  agentPersonality: 'How your assistant comes across',
  agentRemember: 'Always remember',
  meetingPrepTiming: 'Meeting prep timing',
  meetingNotes: 'Meeting notes style',
  updatePreference: 'Update preference',
  reportFormat: 'Longer report format',
  timeSinks: 'What\'s eating the most time',
  neverDo: 'Your assistant should never',
  anythingElse: 'Anything else',
}

function formatValue(key, value) {
  if (!value || (Array.isArray(value) && value.length === 0)) {
    return <span style={{ color: '#6b7280' }}>Not provided</span>
  }
  if (Array.isArray(value)) {
    return (
      <ul className="list-none space-y-1">
        {value.map((v, i) => (
          <li key={i} className="text-sm" style={{ color: '#d1d5db' }}>
            — {v.startsWith('other:') ? `Other: ${v.replace('other:', '')}` : v}
          </li>
        ))}
      </ul>
    )
  }
  return <span className="text-sm" style={{ color: '#d1d5db' }}>{value}</span>
}

export default function SummaryScreen({ formData, onBack }) {
  const [generating, setGenerating] = useState(false)
  const [done, setDone] = useState(false)

  async function handleGenerate() {
    setGenerating(true)
    try {
      const zip = new JSZip()
      const configs = generateAllConfigs(formData)
      for (const [filename, content] of Object.entries(configs)) {
        zip.file(filename, content)
      }
      const blob = await zip.generateAsync({ type: 'blob' })
      const agentName = formData.agentName?.trim()
      const slug = agentName
        ? agentName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
        : 'anonymous'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${slug}-config.zip`
      a.click()
      URL.revokeObjectURL(url)
      setDone(true)
    } finally {
      setGenerating(false)
    }
  }

  const sections = [
    {
      label: 'About You',
      fields: ['name', 'role', 'pronouns'],
    },
    {
      label: 'Your Work Style',
      fields: ['bestThinkingTime', 'focusStyle', 'derailTriggers'],
    },
    {
      label: 'Communication',
      fields: ['communicationStyle', 'infoDelivery', 'difficultNews'],
    },
    {
      label: 'Your Agent',
      fields: ['agentName', 'agentPersonality', 'agentRemember'],
    },
    {
      label: 'Meetings',
      fields: ['meetingPrepTiming', 'meetingNotes'],
    },
    {
      label: 'Information Flow',
      fields: ['updatePreference', 'reportFormat'],
    },
    {
      label: 'Getting Started',
      fields: ['timeSinks', 'neverDo', 'anythingElse'],
    },
  ]

  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-2" style={{ color: '#f3f4f6' }}>
        Review Your Answers
      </h2>
      <p className="text-sm mb-8" style={{ color: '#9ca3af' }}>
        Take a moment to look over everything. You can go back to make changes, or generate your config files when you're ready.
      </p>

      <div className="space-y-8 mb-10">
        {sections.map(section => (
          <div key={section.label}>
            <h3
              className="text-xs font-semibold uppercase tracking-widest mb-3 pb-2"
              style={{ color: '#5eead4', borderBottom: '1px solid #1f2937' }}
            >
              {section.label}
            </h3>
            <div className="space-y-4">
              {section.fields.map(field => (
                <div key={field}>
                  <p className="text-xs mb-1" style={{ color: '#6b7280' }}>
                    {FIELD_LABELS[field] || field}
                  </p>
                  {formatValue(field, formData[field])}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {done && (
        <div
          className="mb-6 px-4 py-3 rounded-md text-sm"
          style={{ backgroundColor: '#0d2d2a', border: '1px solid #5eead4', color: '#99f6e4' }}
        >
          Config files downloaded. Your ZIP is ready to hand off for provisioning.
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={onBack}
          className="px-5 py-2.5 rounded-md text-sm font-medium transition-colors"
          style={{ backgroundColor: '#1f2937', color: '#9ca3af', border: '1px solid #374151' }}
          onMouseEnter={e => { e.target.style.color = '#d1d5db' }}
          onMouseLeave={e => { e.target.style.color = '#9ca3af' }}
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating}
          className="flex-1 px-5 py-2.5 rounded-md text-sm font-medium transition-colors"
          style={{
            backgroundColor: generating ? '#134e4a' : '#0f766e',
            color: generating ? '#6b7280' : '#ccfbf1',
            border: '1px solid #0d9488',
            cursor: generating ? 'not-allowed' : 'pointer',
          }}
        >
          {generating ? 'Generating…' : 'Generate & Download Config Files'}
        </button>
      </div>
    </div>
  )
}
