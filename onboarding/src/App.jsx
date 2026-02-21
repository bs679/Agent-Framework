import { useState } from 'react'
import ProgressBar from './components/ProgressBar'
import SummaryScreen from './components/SummaryScreen'
import AboutYou from './sections/AboutYou'
import WorkStyle from './sections/WorkStyle'
import Communication from './sections/Communication'
import YourAgent from './sections/YourAgent'
import Meetings from './sections/Meetings'
import InfoFlow from './sections/InfoFlow'
import GettingStarted from './sections/GettingStarted'

const SECTIONS = [
  { component: AboutYou,      title: 'About You' },
  { component: WorkStyle,     title: 'Your Work Style' },
  { component: Communication, title: 'Communication' },
  { component: YourAgent,     title: 'Your Agent' },
  { component: Meetings,      title: 'Meetings' },
  { component: InfoFlow,      title: 'Information Flow' },
  { component: GettingStarted, title: 'Getting Started' },
]

// Required fields per section index
const REQUIRED_FIELDS = {
  0: ['name', 'role'],
  6: ['timeSinks'],
}

const EMPTY_FORM = {
  name: '',
  role: '',
  pronouns: '',
  bestThinkingTime: '',
  focusStyle: '',
  derailTriggers: [],
  communicationStyle: '',
  infoDelivery: '',
  difficultNews: '',
  agentName: '',
  agentPersonality: '',
  agentRemember: '',
  meetingPrepTiming: '',
  meetingNotes: '',
  updatePreference: '',
  reportFormat: '',
  timeSinks: '',
  neverDo: '',
  anythingElse: '',
}

function validate(sectionIndex, formData) {
  const required = REQUIRED_FIELDS[sectionIndex] || []
  const errors = {}
  for (const field of required) {
    const val = formData[field]
    const isEmpty = !val || (Array.isArray(val) ? val.length === 0 : !String(val).trim())
    if (isEmpty) {
      errors[field] = 'This field is needed before moving on.'
    }
  }
  return errors
}

export default function App() {
  const [step, setStep] = useState(0)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})

  function handleChange(name, value) {
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  function handleNext() {
    const newErrors = validate(step, formData)
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }
    setErrors({})
    setStep(prev => prev + 1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleBack() {
    setErrors({})
    setStep(prev => Math.max(0, prev - 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const isSummary = step === SECTIONS.length
  const CurrentSection = !isSummary ? SECTIONS[step].component : null

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center"
      style={{ backgroundColor: '#0a0a0f' }}
    >
      <header
        className="w-full px-6 py-4 flex items-center justify-between"
        style={{ borderBottom: '1px solid #1f2937' }}
      >
        <div className="flex items-center gap-3">
          <span
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: '#5eead4', fontFamily: "'JetBrains Mono', monospace" }}
          >
            AIOS
          </span>
          <span className="text-xs" style={{ color: '#374151' }}>|</span>
          <span className="text-xs" style={{ color: '#6b7280' }}>Staff Onboarding</span>
        </div>
        {!isSummary && formData.name && (
          <span className="text-xs" style={{ color: '#6b7280' }}>
            Hi, {formData.name}
          </span>
        )}
      </header>

      <main className="w-full max-w-lg px-5 py-10 flex-1">
        {isSummary ? (
          <SummaryScreen formData={formData} onBack={handleBack} />
        ) : (
          <>
            <ProgressBar
              current={step + 1}
              total={SECTIONS.length}
              title={SECTIONS[step].title}
            />
            <CurrentSection
              formData={formData}
              onChange={handleChange}
              errors={errors}
            />

            {Object.keys(errors).length > 0 && (
              <p className="mt-5 text-sm" style={{ color: '#fbbf24' }}>
                A couple of fields need attention before you continue.
              </p>
            )}

            <div className="flex gap-3 mt-10">
              {step > 0 && (
                <button
                  type="button"
                  onClick={handleBack}
                  className="px-5 py-2.5 rounded-md text-sm font-medium transition-colors"
                  style={{
                    backgroundColor: '#1f2937',
                    color: '#9ca3af',
                    border: '1px solid #374151',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = '#d1d5db' }}
                  onMouseLeave={e => { e.currentTarget.style.color = '#9ca3af' }}
                >
                  ← Back
                </button>
              )}
              <button
                type="button"
                onClick={handleNext}
                className="flex-1 px-5 py-2.5 rounded-md text-sm font-medium transition-colors"
                style={{
                  backgroundColor: '#0f766e',
                  color: '#ccfbf1',
                  border: '1px solid #0d9488',
                }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = '#0d9488' }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#0f766e' }}
              >
                {step === SECTIONS.length - 1 ? 'Review Answers →' : 'Next →'}
              </button>
            </div>
          </>
        )}
      </main>

      <footer className="w-full px-6 py-4 text-center" style={{ borderTop: '1px solid #111827' }}>
        <p className="text-xs" style={{ color: '#374151' }}>
          CHCA District 1199NE — AIOS Agent System
        </p>
      </footer>
    </div>
  )
}
