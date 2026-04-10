import { i } from '@instantdb/admin';

const _schema = i.schema({
  entities: {
    companies: i.entity({
      name: i.string().indexed(),
      website: i.any().optional(),
      industry: i.any().optional(),
      size_estimate: i.any().optional(),
      revenue_estimate: i.any().optional(),
      platform: i.any().optional(),
      search_solution: i.any().optional(),
      social_linkedin: i.any().optional(),
      social_twitter: i.any().optional(),
      social_facebook: i.any().optional(),
      social_other: i.any().optional(),
      tech_stack_notes: i.any().optional(),
      notes: i.any().optional(),
      status: i.string().indexed(),
      created_at: i.string(),
      updated_at: i.string(),
    }),
    contacts: i.entity({
      name: i.string().indexed(),
      email: i.any().optional(),
      role: i.any().optional(),
      phone: i.any().optional(),
      linkedin_url: i.any().optional(),
      status: i.string().indexed(),
      notes: i.any().optional(),
      created_at: i.string(),
      updated_at: i.string(),
    }),
    tags: i.entity({
      name: i.string().unique().indexed(),
      color: i.any().optional(),
      created_at: i.string(),
    }),
    sequences: i.entity({
      name: i.string().indexed(),
      description: i.any().optional(),
      is_active: i.number().indexed(),
      created_at: i.string(),
      updated_at: i.string(),
    }),
    sequenceSteps: i.entity({
      step_order: i.number().indexed(),
      subject_template: i.any().optional(),
      body_template: i.any().optional(),
      delay_days: i.number(),
      created_at: i.string(),
    }),
    enrollments: i.entity({
      current_step: i.number(),
      status: i.string().indexed(),
      started_at: i.string(),
      paused_at: i.any().optional(),
      completed_at: i.any().optional(),
    }),
    events: i.entity({
      status: i.string().indexed(),
      scheduled_date: i.string().indexed(),
      sent_at: i.any().optional(),
      replied_at: i.any().optional(),
      notes: i.any().optional(),
    }),
    reminders: i.entity({
      title: i.string(),
      description: i.any().optional(),
      due_date: i.string().indexed(),
      is_completed: i.number().indexed(),
      created_at: i.string(),
    }),
  },
  links: {
    contactCompany: {
      forward: { on: 'contacts', has: 'one', label: 'company' },
      reverse: { on: 'companies', has: 'many', label: 'contacts' },
    },
    companyTags: {
      forward: { on: 'companies', has: 'many', label: 'tags' },
      reverse: { on: 'tags', has: 'many', label: 'companies' },
    },
    stepSequence: {
      forward: { on: 'sequenceSteps', has: 'one', label: 'sequence' },
      reverse: { on: 'sequences', has: 'many', label: 'steps' },
    },
    enrollmentContact: {
      forward: { on: 'enrollments', has: 'one', label: 'contact' },
      reverse: { on: 'contacts', has: 'many', label: 'enrollments' },
    },
    enrollmentSequence: {
      forward: { on: 'enrollments', has: 'one', label: 'sequence' },
      reverse: { on: 'sequences', has: 'many', label: 'enrollments' },
    },
    eventEnrollment: {
      forward: { on: 'events', has: 'one', label: 'enrollment' },
      reverse: { on: 'enrollments', has: 'many', label: 'events' },
    },
    eventStep: {
      forward: { on: 'events', has: 'one', label: 'step' },
      reverse: { on: 'sequenceSteps', has: 'many', label: 'events' },
    },
    reminderCompany: {
      forward: { on: 'reminders', has: 'one', label: 'company' },
      reverse: { on: 'companies', has: 'many', label: 'reminders' },
    },
    reminderContact: {
      forward: { on: 'reminders', has: 'one', label: 'contact' },
      reverse: { on: 'contacts', has: 'many', label: 'reminders' },
    },
  },
});

type _AppSchema = typeof _schema;
interface AppSchema extends _AppSchema {}
const schema: AppSchema = _schema;
export type { AppSchema };
export default schema;
