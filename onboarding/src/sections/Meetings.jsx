import Section from '../components/Section'
import SelectInput from '../components/SelectInput'

const PREP_TIMING_OPTIONS = [
  { value: '24 hours before', label: '24 hours before' },
  { value: '2 hours before', label: '2 hours before' },
  { value: '30 minutes before', label: '30 minutes before' },
  { value: 'Not applicable', label: 'Not applicable' },
]

const NOTES_OPTIONS = [
  { value: 'Just decisions and action items', label: 'Just decisions and action items' },
  { value: 'Full summary', label: 'Full summary' },
  { value: 'Action items only', label: 'Action items only' },
  { value: "I'll handle my own notes", label: "I'll handle my own notes" },
]

export default function Meetings({ formData, onChange, errors }) {
  return (
    <Section
      title="Meetings"
      description="Your agent can help you prepare for meetings and capture what matters."
    >
      <SelectInput
        label="How far in advance do you want meeting prep?"
        name="meetingPrepTiming"
        value={formData.meetingPrepTiming || ''}
        onChange={e => onChange('meetingPrepTiming', e.target.value)}
        options={PREP_TIMING_OPTIONS}
        error={errors?.meetingPrepTiming}
      />
      <SelectInput
        label="How do you prefer meeting notes captured?"
        name="meetingNotes"
        value={formData.meetingNotes || ''}
        onChange={e => onChange('meetingNotes', e.target.value)}
        options={NOTES_OPTIONS}
        error={errors?.meetingNotes}
      />
    </Section>
  )
}
