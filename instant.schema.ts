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
      report_url: i.string().optional(),
      country: i.string().optional(),
      language: i.string().optional(),
      pdf_url: i.string().optional(),
      pdf_name: i.string().optional(),
      audit_score: i.string().optional(),
      audit_cap_count: i.string().optional(),
      audit_top3rate: i.string().optional(),
      audit_outside3rate: i.string().optional(),
      audit_worst_query: i.string().optional(),
      audit_worst_pos: i.string().optional(),
      audit_wrong_product: i.string().optional(),
      audit_run_at: i.string().optional(),
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
      custom_fields: i.string().optional(),
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
      from_email: i.string().optional(),
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
      experiment_id: i.string().optional(),
      ab_variant: i.string().optional(),
      deal_stage: i.string().optional(),
      send_hour: i.number().optional(),
    }),
    events: i.entity({
      status: i.string().indexed(),
      scheduled_date: i.string().indexed(),
      sent_at: i.any().optional(),
      replied_at: i.any().optional(),
      notes: i.any().optional(),
      resend_email_id: i.string().optional(),
      open_count: i.number().optional(),
      click_count: i.number().optional(),
      opened_at: i.string().optional(),
      clicked_at: i.string().optional(),
    }),
    comments: i.entity({
      body: i.string(),
      created_at: i.string(),
    }),
    experiments: i.entity({
      name: i.string().indexed(),
      status: i.string().indexed(),
      created_at: i.string(),
      updated_at: i.string(),
    }),
    experimentVariants: i.entity({
      label: i.string(),
      created_at: i.string(),
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
    commentContact: {
      forward: { on: 'comments', has: 'one', label: 'contact' },
      reverse: { on: 'contacts', has: 'many', label: 'comments' },
    },
    variantExperiment: {
      forward: { on: 'experimentVariants', has: 'one', label: 'experiment' },
      reverse: { on: 'experiments', has: 'many', label: 'variants' },
    },
    variantSequence: {
      forward: { on: 'experimentVariants', has: 'one', label: 'sequence' },
      reverse: { on: 'sequences', has: 'many', label: 'variants' },
    },
  },
});

type _AppSchema = typeof _schema;
interface AppSchema extends _AppSchema {}
const schema: AppSchema = _schema;
export type { AppSchema };
export default schema;
