import Section from '../components/Section'
import TextInput from '../components/TextInput'
import SelectInput from '../components/SelectInput'
import TextArea from '../components/TextArea'

const PERSONALITY_OPTIONS = [
  { value: 'Calm and supportive', label: 'Calm and supportive' },
  { value: 'Focused and efficient', label: 'Focused and efficient' },
  { value: 'Warm and collaborative', label: 'Warm and collaborative' },
  { value: 'Adaptive', label: 'Adaptive' },
]

export default function YourAgent({ formData, onChange, errors }) {
  return (
    <Section
      title="Your Agent"
      description="Let's shape who your agent is — or let it figure that out on its own."
    >
      <TextInput
        label="What should your assistant be called?"
        name="agentName"
        value={formData.agentName || ''}
        onChange={e => onChange('agentName', e.target.value)}
        placeholder="Give them a name, or leave blank"
        helper="Leave blank and your agent will choose its own name on first boot."
        error={errors?.agentName}
      />
      <SelectInput
        label="How should your assistant come across?"
        name="agentPersonality"
        value={formData.agentPersonality || ''}
        onChange={e => onChange('agentPersonality', e.target.value)}
        options={PERSONALITY_OPTIONS}
        error={errors?.agentPersonality}
      />
      <TextArea
        label="Anything your assistant should always remember about you?"
        name="agentRemember"
        value={formData.agentRemember || ''}
        onChange={e => onChange('agentRemember', e.target.value)}
        placeholder="Things that are easy to forget but matter a lot — context, history, preferences…"
        error={errors?.agentRemember}
      />
    </Section>
  )
}
