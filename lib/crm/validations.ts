import { z } from 'zod';

export const companyCreateSchema = z.object({
  name: z.string().min(1, 'Company name is required'),
  website: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
  size_estimate: z.string().nullable().optional(),
  revenue_estimate: z.string().nullable().optional(),
  platform: z.string().nullable().optional(),
  social_linkedin: z.string().nullable().optional(),
  social_twitter: z.string().nullable().optional(),
  social_facebook: z.string().nullable().optional(),
  social_other: z.string().nullable().optional(),
  tech_stack_notes: z.string().nullable().optional(),
  search_solution: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  status: z.enum(['prospect', 'contacted', 'in-sequence', 'replied', 'meeting-booked', 'won', 'lost', 'not-interested']).default('prospect'),
  tag_ids: z.array(z.string()).optional(),
  report_url: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  language: z.string().nullable().optional(),
});

export const companyUpdateSchema = companyCreateSchema.partial();

export const contactCreateSchema = z.object({
  company_id: z.string().min(1, 'Company is required'),
  name: z.string().min(1, 'Contact name is required'),
  email: z.string().email('Valid email is required'),
  role: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  linkedin_url: z.string().nullable().optional(),
  status: z.enum(['active', 'bounced', 'unsubscribed', 'replied']).default('active'),
  notes: z.string().nullable().optional(),
  custom_fields: z.record(z.string(), z.string()).nullable().optional(),
});

export const contactUpdateSchema = contactCreateSchema.partial();

export const sequenceCreateSchema = z.object({
  name: z.string().min(1, 'Sequence name is required'),
  description: z.string().nullable().optional(),
  is_active: z.union([z.boolean(), z.number().int().min(0).max(1)]).transform(v => (typeof v === 'boolean' ? (v ? 1 : 0) : v)).default(1),
  from_email: z.string().email().nullable().optional(),
});

export const sequenceUpdateSchema = sequenceCreateSchema.partial();

export const stepCreateSchema = z.object({
  step_order: z.number().int().positive(),
  subject_template: z.string().nullable().optional(),
  body_template: z.string().nullable().optional(),
  delay_days: z.number().int().min(0).default(0),
});

export const stepUpdateSchema = stepCreateSchema.partial();

export const enrollContactSchema = z.object({
  contact_ids: z.array(z.string().min(1)).min(1),
  sequence_id: z.string().min(1, 'Sequence is required'),
  send_hour: z.number().int().min(0).max(23).optional(),
});

export const reminderCreateSchema = z.object({
  company_id: z.string().nullable().optional(),
  contact_id: z.string().nullable().optional(),
  title: z.string().min(1, 'Title is required'),
  description: z.string().nullable().optional(),
  due_date: z.string().min(1, 'Due date is required'),
});

export const reminderUpdateSchema = reminderCreateSchema.partial().extend({
  is_completed: z.number().int().min(0).max(1).optional(),
});

export const tagCreateSchema = z.object({
  name: z.string().min(1, 'Tag name is required'),
  color: z.string().nullable().optional(),
});
