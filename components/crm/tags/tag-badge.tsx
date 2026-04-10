import { X } from "lucide-react";

interface TagBadgeProps {
  name: string;
  color?: string | null;
  onRemove?: () => void;
}

export function TagBadge({ name, color, onRemove }: TagBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium"
      style={{
        backgroundColor: color ? `${color}15` : '#f1f5f9',
        borderColor: color ? `${color}40` : '#e2e8f0',
        color: color || '#475569',
      }}
    >
      {name}
      {onRemove && (
        <button onClick={onRemove} className="ml-0.5 hover:opacity-70" type="button">
          <X className="h-2.5 w-2.5" />
        </button>
      )}
    </span>
  );
}
