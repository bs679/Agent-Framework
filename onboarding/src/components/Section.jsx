export default function Section({ title, description, children }) {
  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-2" style={{ color: '#f3f4f6' }}>
        {title}
      </h2>
      {description && (
        <p className="text-sm mb-8" style={{ color: '#9ca3af' }}>
          {description}
        </p>
      )}
      <div className="space-y-6">
        {children}
      </div>
    </div>
  )
}
