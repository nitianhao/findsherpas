import { adminDb, id } from '@/lib/crm/instant-db';
import type { Tag } from '@/lib/crm/types';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTag(t: any): Tag {
  return {
    id: t.id as string,
    name: t.name ?? '',
    color: t.color ?? null,
    created_at: t.created_at ?? now(),
  };
}

export async function getTags(): Promise<Tag[]> {
  const data = await adminDb.query({ tags: {} });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.tags as any[]).map(mapTag).sort((a, b) => a.name.localeCompare(b.name));
}

export async function createTag(name: string, color: string | null = null): Promise<Tag> {
  const tagId = id();
  await adminDb.transact(
    adminDb.tx.tags[tagId].update({ name, color, created_at: now() })
  );
  const data = await adminDb.query({ tags: { $: { where: { id: tagId } } } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return mapTag((data.tags as any[])[0]);
}

export async function deleteTag(tagId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.tags[tagId].delete());
}

export async function setCompanyTags(companyId: string, tagIds: string[]): Promise<void> {
  const data = await adminDb.query({
    companies: { $: { where: { id: companyId } }, tags: { $: { fields: ['id'] } } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const currentTagIds = ((data.companies as any[])[0]?.tags ?? []).map((t: { id: string }) => t.id) as string[];

  const txns = [];
  if (currentTagIds.length > 0) {
    txns.push(adminDb.tx.companies[companyId].unlink({ tags: currentTagIds }));
  }
  if (tagIds.length > 0) {
    txns.push(adminDb.tx.companies[companyId].link({ tags: tagIds }));
  }
  if (txns.length > 0) {
    await adminDb.transact(txns);
  }
}
