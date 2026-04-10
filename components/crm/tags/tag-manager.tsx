"use client";

import { useState } from "react";
import { Tag } from "@/lib/crm/types";
import { TagBadge } from "./tag-badge";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

export function TagManager({ initialTags }: { initialTags: Tag[] }) {
  const router = useRouter();
  const [tags, setTags] = useState(initialTags);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#3b82f6");

  async function addTag() {
    if (!newName.trim()) return;
    const res = await fetch("/api/crm/tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName.trim(), color: newColor }),
    });
    if (res.ok) {
      const tag = await res.json();
      setTags([...tags, tag]);
      setNewName("");
      toast.success("Tag created");
      router.refresh();
    } else {
      toast.error("Failed to create tag");
    }
  }

  async function removeTag(id: string) {
    const res = await fetch(`/api/crm/tags/${id}`, { method: "DELETE" });
    if (res.ok) {
      setTags(tags.filter((t) => t.id !== id));
      toast.success("Tag deleted");
      router.refresh();
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <TagBadge
            key={tag.id}
            name={tag.name}
            color={tag.color}
            onRemove={() => removeTag(tag.id)}
          />
        ))}
        {tags.length === 0 && (
          <p className="text-sm text-muted-foreground">No tags yet.</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Tag name"
          className="max-w-[200px]"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
        />
        <input
          type="color"
          value={newColor}
          onChange={(e) => setNewColor(e.target.value)}
          className="h-8 w-8 rounded border cursor-pointer"
        />
        <Button onClick={addTag} size="sm">
          <Plus className="mr-1 h-3 w-3" />
          Add
        </Button>
      </div>
    </div>
  );
}
