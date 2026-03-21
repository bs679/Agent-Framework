import Section from '../components/Section'
import SelectInput from '../components/SelectInput'
import MultiSelect from '../components/MultiSelect'

const THINKING_TIME_OPTIONS = [
  { value: 'Early morning', label: 'Early morning' },
  { value: 'Mid-morning', label: 'Mid-morning' },
  { value: 'Afternoon', label: 'Afternoon' },
  { value: 'Evening', label: 'Evening' },
  { value: 'It varies', label: 'It varies' },
]

const FOCUS_OPTIONS = [
  { value: 'Long uninterrupted blocks', label: 'Long uninterrupted blocks' },
  { value: 'Short sprints with breaks', label: 'Short sprints with breaks' },
  { value: 'I go with the flow', label: 'I go with the flow' },
]

const DERAIL_OPTIONS = [
  { value: 'Too many open tabs/tasks', label: 'Too many open tabs/tasks' },
  { value: 'Unclear priorities', label: 'Unclear priorities' },
  { value: 'Unexpected interruptions', label: 'Unexpected interruptions' },
  { value: 'Back-to-back meetings', label: 'Back-to-back meetings' },
  { value: 'Emotional conversations', label: 'Emotional conversations' },
  { value: 'Noise or environment', label: 'Noise or environment' },
  { value: 'other', label: 'Other' },
]

export default function WorkStyle({ formData, onChange, errors }) {
  return (
    <Section
      title="Your Work Style"
      description="Your agent will use this to know when to help and when to stay out of the way."
    >
      <SelectInput
        label="When do you do your best thinking?"
        name="bestThinkingTime"
        value={formData.bestThinkingTime || ''}
        onChange={e => onChange('bestThinkingTime', e.target.value)}
        options={THINKING_TIME_OPTIONS}
        error={errors?.bestThinkingTime}
      />
      <SelectInput
        label="How do you prefer to focus?"
        name="focusStyle"
        value={formData.focusStyle || ''}
        onChange={e => onChange('focusStyle', e.target.value)}
        options={FOCUS_OPTIONS}
        error={errors?.focusStyle}
      />
      <MultiSelect
        label="What tends to derail you?"
        name="derailTriggers"
        value={formData.derailTriggers || []}
        onChange={onChange}
        options={DERAIL_OPTIONS}
        helper="Select all that apply."
        error={errors?.derailTriggers}
      />
    </Section>
  )
}
