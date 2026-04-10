"use client";

import { useState } from "react";
import type { Comment } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Textarea } from "@/components/crm/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { Trash2, MessageSquare } from "lucide-react";
import { toast } from "sonner";

interface ContactCommentsProps {
  contactId: string;
  initialComments: Comment[];
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ContactComments({ contactId, initialComments }: ContactCommentsProps) {
  const [comments, setComments] = useState(initialComments);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(`/api/crm/contacts/${contactId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      if (res.ok) {
        const comment: Comment = await res.json();
        setComments((prev) => [comment, ...prev]);
        setBody("");
      } else {
        const err = await res.json();
        toast.error(err.error || "Failed to add comment");
      }
    } catch {
      toast.error("Failed to add comment");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: string) {
    setDeleting((prev) => new Set(prev).add(commentId));
    try {
      const res = await fetch(`/api/crm/contacts/${contactId}/comments`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment_id: commentId }),
      });
      if (res.ok) {
        setComments((prev) => prev.filter((c) => c.id !== commentId));
      } else {
        toast.error("Failed to delete comment");
      }
    } catch {
      toast.error("Failed to delete comment");
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Comments
          {comments.length > 0 && (
            <span className="text-muted-foreground font-normal">({comments.length})</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleSubmit} className="space-y-2">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Add a comment..."
            rows={3}
          />
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={submitting || !body.trim()}>
              {submitting ? "Adding..." : "Add Comment"}
            </Button>
          </div>
        </form>

        {comments.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No comments yet.</p>
        ) : (
          <div className="space-y-3">
            {comments.map((comment) => (
              <div key={comment.id} className="flex gap-3 group">
                <div className="flex-1 min-w-0 rounded-md border bg-muted/30 px-3 py-2 space-y-1">
                  <p className="text-sm whitespace-pre-wrap">{comment.body}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(comment.created_at)}</p>
                </div>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  className="opacity-0 group-hover:opacity-100 shrink-0 mt-1"
                  onClick={() => handleDelete(comment.id)}
                  disabled={deleting.has(comment.id)}
                >
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
