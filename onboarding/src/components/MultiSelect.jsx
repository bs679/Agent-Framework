import { useState } from 'react'

export default function MultiSelect({ label, name, value = [], onChange, options, required, helper, error }) {
  const [otherText, setOtherText] = useState(
    value.find(v => v.startsWith('other:'))?.replace('other:', '') || ''
  )

  const hasOtherOption = options.some(o => o.value === 'other')

  function toggle(optValue) {
    if (optValue === 'other') {
      const hasOther = value.some(v => v.startsWith('other:'))
      if (hasOther) {
        onChange(name, value.filter(v => !v.startsWith('other:')))
      } else {
        onChange(name, [...value, 'other:'])
      }
    } else {
      if (value.includes(optValue)) {
        onChange(name, value.filter(v => v !== optValue))
      } else {
        onChange(name, [...value, optValue])
      }
    }
  }

  function handleOtherText(e) {
    const text = e.target.value
    setOtherText(text)
    const without = value.filter(v => !v.startsWith('other:'))
    onChange(name, [...without, `other:${text}`])
  }

  const isOtherChecked = value.some(v => v.startsWith('other:'))

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium" style={{ color: '#d1d5db' }}>
        {label}
        {required && <span className="ml-1" style={{ color: '#9ca3af' }}>*</span>}
      </label>
      {helper && (
        <p className="text-xs" style={{ color: '#6b7280' }}>{helper}</p>
      )}
      <div className="flex flex-col gap-2">
        {options.filter(o => o.value !== 'other').map(opt => (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-left transition-colors"
            style={{
              backgroundColor: value.includes(opt.value) ? '#0d2d2a' : '#111118',
              border: `1px solid ${value.includes(opt.value) ? '#5eead4' : '#374151'}`,
              color: value.includes(opt.value) ? '#99f6e4' : '#d1d5db',
            }}
          >
            <span
              className="flex-shrink-0 w-4 h-4 rounded flex items-center justify-center"
              style={{
                backgroundColor: value.includes(opt.value) ? '#5eead4' : 'transparent',
                border: `1px solid ${value.includes(opt.value) ? '#5eead4' : '#6b7280'}`,
              }}
            >
              {value.includes(opt.value) && (
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M2 5l2.5 2.5L8 2.5" stroke="#0a0a0f" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </span>
            {opt.label}
          </button>
        ))}
        {hasOtherOption && (
          <>
            <button
              type="button"
              onClick={() => toggle('other')}
              className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-left transition-colors"
              style={{
                backgroundColor: isOtherChecked ? '#0d2d2a' : '#111118',
                border: `1px solid ${isOtherChecked ? '#5eead4' : '#374151'}`,
                color: isOtherChecked ? '#99f6e4' : '#d1d5db',
              }}
            >
              <span
                className="flex-shrink-0 w-4 h-4 rounded flex items-center justify-center"
                style={{
                  backgroundColor: isOtherChecked ? '#5eead4' : 'transparent',
                  border: `1px solid ${isOtherChecked ? '#5eead4' : '#6b7280'}`,
                }}
              >
                {isOtherChecked && (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 2.5" stroke="#0a0a0f" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </span>
              Other
            </button>
            {isOtherChecked && (
              <input
                type="text"
                value={otherText}
                onChange={handleOtherText}
                placeholder="Tell us more…"
                className="w-full px-3 py-2.5 rounded-md text-sm outline-none ml-7"
                style={{
                  backgroundColor: '#111118',
                  border: '1px solid #5eead4',
                  color: '#f3f4f6',
                }}
              />
            )}
          </>
        )}
      </div>
      {error && (
        <p className="text-xs mt-1" style={{ color: '#fbbf24' }}>{error}</p>
      )}
    </div>
  )
}
