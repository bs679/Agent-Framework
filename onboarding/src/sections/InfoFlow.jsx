import Section from '../components/Section'
import SelectInput from '../components/SelectInput'

const UPDATE_OPTIONS = [
  { value: 'Push them to me proactively', label: 'Push them to me proactively' },
  { value: "I'll ask when I need them", label: "I'll ask when I need them" },
  { value: 'Morning summary + flag urgent items only', label: 'Morning summary + flag urgent items only' },
]

const REPORT_FORMAT_OPTIONS = [
  { value: 'Executive summary up top', label: 'Executive summary up top' },
  { value: 'Just the highlights', label: 'Just the highlights' },
  { value: 'Full detail', label: 'Full detail' },
  { value: 'Whatever fits the content', label: 'Whatever fits the content' },
]

export default function InfoFlow({ formData, onChange, errors }) {
  return (
    <Section
      title="Information Flow"
      description="How your agent keeps you informed — without overwhelming you."
    >
      <SelectInput
        label="How do you prefer updates during the day?"
        name="updatePreference"
        value={formData.updatePreference || ''}
        onChange={e => onChange('updatePreference', e.target.value)}
        options={UPDATE_OPTIONS}
        error={errors?.updatePreference}
      />
      <SelectInput
        label="What format for longer reports?"
        name="reportFormat"
        value={formData.reportFormat || ''}
        onChange={e => onChange('reportFormat', e.target.value)}
        options={REPORT_FORMAT_OPTIONS}
        error={errors?.reportFormat}
      />
    </Section>
  )
}
