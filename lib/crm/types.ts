export interface Company {
  id: string;
  name: string;
  website: string | null;
  industry: string | null;
  size_estimate: string | null;
  revenue_estimate: string | null;
  platform: string | null;
  social_linkedin: string | null;
  social_twitter: string | null;
  social_facebook: string | null;
  social_other: string | null;
  tech_stack_notes: string | null;
  search_solution: string | null;
  notes: string | null;
  status: CompanyStatus;
  report_url: string | null;
  country: string | null;
  language: string | null;
  pdf_url: string | null;
  pdf_name: string | null;
  audit_score: string | null;
  audit_cap_count: string | null;
  audit_top3rate: string | null;
  audit_outside3rate: string | null;
  audit_worst_query: string | null;
  audit_worst_pos: string | null;
  audit_wrong_product: string | null;
  audit_run_at: string | null;
  created_at: string;
  updated_at: string;
  contacts_count?: number;
  tags?: Tag[];
}

export type CompanyStatus = 'prospect' | 'contacted' | 'in-sequence' | 'replied' | 'meeting-booked' | 'won' | 'lost' | 'not-interested';

export interface Contact {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: string | null;
  phone: string | null;
  linkedin_url: string | null;
  status: ContactStatus;
  notes: string | null;
  custom_fields: Record<string, string> | null;
  created_at: string;
  updated_at: string;
  company_name?: string;
}

export type ContactStatus = 'active' | 'bounced' | 'unsubscribed' | 'replied';

export interface Tag {
  id: string;
  name: string;
  color: string | null;
  created_at: string;
}

export interface Sequence {
  id: string;
  name: string;
  description: string | null;
  is_active: number;
  from_email: string | null;
  created_at: string;
  updated_at: string;
  steps_count?: number;
  enrolled_count?: number;
}

export interface SequenceStep {
  id: string;
  sequence_id: string;
  step_order: number;
  subject_template: string | null;
  body_template: string | null;
  delay_days: number;
  created_at: string;
}

export interface ContactSequence {
  id: string;
  contact_id: string;
  sequence_id: string;
  current_step: number;
  status: EnrollmentStatus;
  started_at: string;
  paused_at: string | null;
  completed_at: string | null;
  deal_stage: string | null;
  send_hour: number | null;
  contact_name?: string;
  contact_email?: string;
  company_name?: string;
  sequence_name?: string;
}

export type EnrollmentStatus = 'active' | 'paused' | 'completed' | 'replied' | 'bounced';

export interface ContactSequenceEvent {
  id: string;
  contact_sequence_id: string;
  step_id: string;
  status: EventStatus;
  scheduled_date: string | null;
  sent_at: string | null;
  replied_at: string | null;
  notes: string | null;
  open_count: number;
  click_count: number;
  opened_at: string | null;
  clicked_at: string | null;
  step_order?: number;
  subject_template?: string | null;
  body_template?: string | null;
}

export type EventStatus = 'pending' | 'scheduled' | 'sent' | 'replied' | 'bounced' | 'skipped';

export interface Reminder {
  id: string;
  company_id: string | null;
  contact_id: string | null;
  title: string;
  description: string | null;
  due_date: string;
  is_completed: number;
  created_at: string;
  company_name?: string;
  contact_name?: string;
}

export interface Comment {
  id: string;
  contact_id: string;
  body: string;
  created_at: string;
}

export interface ExperimentVariant {
  id: string;
  label: 'A' | 'B';
  sequence_id: string;
  sequence_name: string;
  enrolled: number;
  sent: number;
  replied: number;
}

export interface Experiment {
  id: string;
  name: string;
  status: 'active' | 'ended';
  created_at: string;
  updated_at: string;
  variants: ExperimentVariant[];
}

export interface DashboardStats {
  total_companies: number;
  total_contacts: number;
  emails_sent: number;
  response_rate: number;
  meetings_booked: number;
  tasks_due_today: number;
}

export interface TodayTask {
  type: 'email' | 'reminder';
  id: string;
  contact_name?: string;
  contact_email?: string;
  company_name?: string;
  company_id?: string;
  subject?: string;
  body?: string;
  step_order?: number;
  sequence_name?: string;
  event_id?: string;
  scheduled_date: string;
  send_hour?: number | null;
  is_overdue: boolean;
  title?: string;
  description?: string;
  reminder_id?: string;
}

export interface ActivityItem {
  type: 'email_sent' | 'email_opened' | 'email_clicked' | 'email_replied' | 'email_bounced' | 'email_skipped' | 'comment' | 'reminder';
  date: string;
  description: string;
}
