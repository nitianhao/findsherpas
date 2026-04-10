import { NextRequest, NextResponse } from 'next/server';
import { getCommentsByContactId, createComment, deleteComment } from '@/lib/crm/queries/comments';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: contactId } = await params;
    const comments = await getCommentsByContactId(contactId);
    return NextResponse.json(comments);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch comments' },
      { status: 500 }
    );
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: contactId } = await params;
    const { body } = await req.json();
    if (!body || typeof body !== 'string' || !body.trim()) {
      return NextResponse.json({ error: 'Comment body is required' }, { status: 400 });
    }
    const comment = await createComment(contactId, body.trim());
    return NextResponse.json(comment, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create comment' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    await params; // consume params
    const { comment_id } = await req.json();
    if (!comment_id) return NextResponse.json({ error: 'comment_id required' }, { status: 400 });
    await deleteComment(comment_id);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete comment' },
      { status: 500 }
    );
  }
}
