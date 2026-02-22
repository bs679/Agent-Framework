export default function ProgressBar({ current, total, title }) {
  return (
    <div className="mb-8">
      <p className="text-sm font-medium" style={{ color: '#5eead4' }}>
        Step {current} of {total} — {title}
      </p>
    </div>
  )
}
