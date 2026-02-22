export default function TextArea({ label, name, value, onChange, placeholder, required, helper, error, rows = 4 }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium" style={{ color: '#d1d5db' }}>
        {label}
        {required && <span className="ml-1" style={{ color: '#9ca3af' }}>*</span>}
      </label>
      {helper && (
        <p className="text-xs" style={{ color: '#6b7280' }}>{helper}</p>
      )}
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
        className="w-full px-3 py-2.5 rounded-md text-sm outline-none transition-colors resize-y"
        style={{
          backgroundColor: '#111118',
          border: `1px solid ${error ? '#d97706' : '#374151'}`,
          color: '#f3f4f6',
          minHeight: '100px',
        }}
        onFocus={e => { e.target.style.borderColor = '#5eead4' }}
        onBlur={e => { e.target.style.borderColor = error ? '#d97706' : '#374151' }}
      />
      {error && (
        <p className="text-xs" style={{ color: '#fbbf24' }}>{error}</p>
      )}
    </div>
  )
}
