export default function SelectInput({ label, name, value, onChange, options, required, helper, error }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium" style={{ color: '#d1d5db' }}>
        {label}
        {required && <span className="ml-1" style={{ color: '#9ca3af' }}>*</span>}
      </label>
      {helper && (
        <p className="text-xs" style={{ color: '#6b7280' }}>{helper}</p>
      )}
      <select
        name={name}
        value={value}
        onChange={onChange}
        className="w-full px-3 py-2.5 rounded-md text-sm outline-none transition-colors appearance-none cursor-pointer"
        style={{
          backgroundColor: '#111118',
          border: `1px solid ${error ? '#d97706' : '#374151'}`,
          color: value ? '#f3f4f6' : '#6b7280',
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 12px center',
          paddingRight: '36px',
        }}
        onFocus={e => { e.target.style.borderColor = '#5eead4' }}
        onBlur={e => { e.target.style.borderColor = error ? '#d97706' : '#374151' }}
      >
        <option value="" disabled>Select one…</option>
        {options.map(opt => (
          <option key={opt.value} value={opt.value} style={{ backgroundColor: '#111118', color: '#f3f4f6' }}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="text-xs" style={{ color: '#fbbf24' }}>{error}</p>
      )}
    </div>
  )
}
