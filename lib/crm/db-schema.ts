import type Database from 'better-sqlite3';

export function initializeSchema(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS companies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      website TEXT,
      industry TEXT,
      size_estimate TEXT,
      revenue_estimate TEXT,
      platform TEXT,
      social_linkedin TEXT,
      social_twitter TEXT,
      social_facebook TEXT,
      social_other TEXT,
      tech_stack_notes TEXT,
      search_solution TEXT,
      notes TEXT,
      status TEXT NOT NULL DEFAULT 'prospect',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      color TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS company_tags (
      company_id INTEGER NOT NULL,
      tag_id INTEGER NOT NULL,
      PRIMARY KEY (company_id, tag_id),
      FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
      FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS contacts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      role TEXT,
      phone TEXT,
      linkedin_url TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      notes TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sequences (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sequence_steps (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sequence_id INTEGER NOT NULL,
      step_order INTEGER NOT NULL,
      subject_template TEXT,
      body_template TEXT,
      delay_days INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE(sequence_id, step_order),
      FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS contact_sequences (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      contact_id INTEGER NOT NULL,
      sequence_id INTEGER NOT NULL,
      current_step INTEGER NOT NULL DEFAULT 1,
      status TEXT NOT NULL DEFAULT 'active',
      started_at TEXT NOT NULL DEFAULT (datetime('now')),
      paused_at TEXT,
      completed_at TEXT,
      UNIQUE(contact_id, sequence_id),
      FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
      FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS contact_sequence_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      contact_sequence_id INTEGER NOT NULL,
      step_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      scheduled_date TEXT,
      sent_at TEXT,
      replied_at TEXT,
      notes TEXT,
      UNIQUE(contact_sequence_id, step_id),
      FOREIGN KEY (contact_sequence_id) REFERENCES contact_sequences(id) ON DELETE CASCADE,
      FOREIGN KEY (step_id) REFERENCES sequence_steps(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reminders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER,
      contact_id INTEGER,
      title TEXT NOT NULL,
      description TEXT,
      due_date TEXT NOT NULL,
      is_completed INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
      FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
    CREATE INDEX IF NOT EXISTS idx_companies_platform ON companies(platform);
    CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
    CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
    CREATE INDEX IF NOT EXISTS idx_contact_sequences_contact_id ON contact_sequences(contact_id);
    CREATE INDEX IF NOT EXISTS idx_contact_sequences_sequence_id ON contact_sequences(sequence_id);
    CREATE INDEX IF NOT EXISTS idx_contact_sequences_status ON contact_sequences(status);
    CREATE INDEX IF NOT EXISTS idx_contact_sequence_events_scheduled_date ON contact_sequence_events(scheduled_date);
    CREATE INDEX IF NOT EXISTS idx_contact_sequence_events_status ON contact_sequence_events(status);
    CREATE INDEX IF NOT EXISTS idx_reminders_due_date ON reminders(due_date);
    CREATE INDEX IF NOT EXISTS idx_reminders_is_completed ON reminders(is_completed);
    CREATE INDEX IF NOT EXISTS idx_company_tags_tag_id ON company_tags(tag_id);
  `);
}
