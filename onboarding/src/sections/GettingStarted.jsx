import Section from '../components/Section'
import TextArea from '../components/TextArea'

export default function GettingStarted({ formData, onChange, errors }) {
  return (
    <Section
      title="Getting Started"
      description="This is where your agent gets its first real context about your work and your world."
    >
      <TextArea
        label="What's eating the most time in your week right now?"
        name="timeSinks"
        value={formData.timeSinks || ''}
        onChange={e => onChange('timeSinks', e.target.value)}
        placeholder="Example: chasing expense reports, scheduling conflicts, keeping up with email…"
        required
        rows={4}
        error={errors?.timeSinks}
      />
      <TextArea
        label="Is there anything your assistant should never do?"
        name="neverDo"
        value={formData.neverDo || ''}
        onChange={e => onChange('neverDo', e.target.value)}
        placeholder="Example: Never send an email on my behalf without my approval."
        rows={3}
        error={errors?.neverDo}
      />
      <TextArea
        label="Anything else you want your agent to know?"
        name="anythingElse"
        value={formData.anythingElse || ''}
        onChange={e => onChange('anythingElse', e.target.value)}
        placeholder="Context, quirks, preferences, history — anything that would help."
        rows={3}
        error={errors?.anythingElse}
      />
    </Section>
  )
}
