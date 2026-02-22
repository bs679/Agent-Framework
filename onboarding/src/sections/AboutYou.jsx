import Section from '../components/Section'
import TextInput from '../components/TextInput'
import SelectInput from '../components/SelectInput'

const ROLE_OPTIONS = [
  { value: 'President', label: 'President' },
  { value: 'Secretary-Treasurer', label: 'Secretary-Treasurer' },
  { value: 'Executive Secretary', label: 'Executive Secretary' },
  { value: 'Staff', label: 'Staff' },
]

export default function AboutYou({ formData, onChange, errors }) {
  return (
    <Section
      title="About You"
      description="Just the basics — this helps your agent understand who it's working with."
    >
      <TextInput
        label="Your name"
        name="name"
        value={formData.name || ''}
        onChange={e => onChange('name', e.target.value)}
        placeholder="Your first name, or whatever you go by"
        required
        error={errors?.name}
      />
      <SelectInput
        label="Your role"
        name="role"
        value={formData.role || ''}
        onChange={e => onChange('role', e.target.value)}
        options={ROLE_OPTIONS}
        required
        error={errors?.role}
      />
      <TextInput
        label="Your pronouns"
        name="pronouns"
        value={formData.pronouns || ''}
        onChange={e => onChange('pronouns', e.target.value)}
        placeholder="they/them, she/her, he/him, etc."
      />
    </Section>
  )
}
