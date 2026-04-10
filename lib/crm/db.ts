import Database from 'better-sqlite3';
import path from 'path';
import { initializeSchema } from './db-schema';

const DB_PATH = path.join(process.cwd(), 'data', 'crm.db');

const globalForDb = globalThis as unknown as { db: Database.Database };

function createDb(): Database.Database {
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  initializeSchema(db);
  return db;
}

export function getDb(): Database.Database {
  if (process.env.NODE_ENV === 'production') {
    return globalForDb.db ?? (globalForDb.db = createDb());
  }
  // In dev, use globalThis to survive HMR
  if (!globalForDb.db) {
    globalForDb.db = createDb();
  }
  return globalForDb.db;
}
