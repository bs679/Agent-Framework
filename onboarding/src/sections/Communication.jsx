import Section from '../components/Section'
import SelectInput from '../components/SelectInput'

const COMM_STYLE_OPTIONS = [
  { value: 'Brief and direct', label: 'Brief and direct' },
  { value: 'Detailed and thorough', label: 'Detailed and thorough' },
  { value: 'Match my energy', label: 'Match my energy' },
]

const INFO_DELIVERY_OPTIONS = [
  { value: 'Bullet points', label: 'Bullet points' },
  { value: 'Flowing prose', label: 'Flowing prose' },
  { value: 'Tables and structure', label: 'Tables and structure' },
  { value: 'Mix it up', label: 'Mix it up' },
]

const DIFFICULT_NEWS_OPTIONS = [
  { value: 'Lead with the bottom line', label: 'Lead with the bottom line' },
  { value: 'Give me context first', label: 'Give me context first' },
  { value: 'Ask me how I want to hear it', label: 'Ask me how I want to hear it' },
]

export default function Communication({ formData, onChange, errors }) {
  return (
    <Section
      title="Communication"
      description="This shapes how your agent talks to you — tone, format, and the hard stuff."
    >
      <SelectInput
        label="How should your assistant communicate with you?"
        name="communicationStyle"
        value={formData.communicationStyle || ''}
        onChange={e => onChange('communicationStyle', e.target.value)}
        options={COMM_STYLE_OPTIONS}
        error={errors?.communicationStyle}
      />
      <SelectInput
        label="How do you like information delivered?"
        name="infoDelivery"
        value={formData.infoDelivery || ''}
        onChange={e => onChange('infoDelivery', e.target.value)}
        options={INFO_DELIVERY_OPTIONS}
        error={errors?.infoDelivery}
      />
      <SelectInput
        label="When there's difficult news, how should your assistant tell you?"
        name="difficultNews"
        value={formData.difficultNews || ''}
        onChange={e => onChange('difficultNews', e.target.value)}
        options={DIFFICULT_NEWS_OPTIONS}
        error={errors?.difficultNews}
      />
    </Section>
  )
}
