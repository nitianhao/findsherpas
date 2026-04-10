import { adminDb, id } from '@/lib/crm/instant-db';
import type { Comment } from '@/lib/crm/types';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapComment(c: any): Comment {
  return {
    id: c.id as string,
    contact_id: c.contact?.id ?? '',
    body: c.body ?? '',
    created_at: c.created_at ?? now(),
  };
}

export async function getCommentsByContactId(contactId: string): Promise<Comment[]> {
  const data = await adminDb.query({
    comments: { $: { where: { 'contact.id': contactId } }, contact: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.comments as any[]).map(mapComment)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function createComment(contactId: string, body: string): Promise<Comment> {
  const commentId = id();
  const ts = now();
  await adminDb.transact([
    adminDb.tx.comments[commentId].update({ body, created_at: ts }),
    adminDb.tx.comments[commentId].link({ contact: contactId }),
  ]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await adminDb.query({ comments: { $: { where: { id: commentId } }, contact: {} } });
  return mapComment((data.comments as any[])[0]);
}

export async function deleteComment(commentId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.comments[commentId].delete());
}
