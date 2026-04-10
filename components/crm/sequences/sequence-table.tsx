"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Sequence } from "@/lib/crm/types";
import { DataTable } from "@/components/crm/shared/data-table";
import { Badge } from "@/components/crm/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/crm/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

const columns: ColumnDef<Sequence>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link href={`/crm/sequences/${row.original.id}`} className="font-medium hover:underline">
        {row.getValue("name")}
      </Link>
    ),
  },
  {
    accessorKey: "steps_count",
    header: "Steps",
    cell: ({ row }) => row.original.steps_count ?? 0,
  },
  {
    accessorKey: "enrolled_count",
    header: "Enrolled",
    cell: ({ row }) => row.original.enrolled_count ?? 0,
  },
  {
    accessorKey: "is_active",
    header: "Status",
    cell: ({ row }) => {
      const isActive = row.original.is_active === 1;
      return (
        <Badge variant={isActive ? "default" : "secondary"}>
          {isActive ? "Active" : "Inactive"}
        </Badge>
      );
    },
  },
  {
    id: "actions",
    cell: function ActionsCell({ row }) {
      const router = useRouter();
      const sequence = row.original;

      async function handleDelete() {
        if (!confirm("Delete this sequence? This cannot be undone.")) return;
        const res = await fetch(`/api/crm/sequences/${sequence.id}`, { method: "DELETE" });
        if (res.ok) {
          toast.success("Sequence deleted");
          router.refresh();
        } else {
          toast.error("Failed to delete sequence");
        }
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger className="h-8 w-8 p-0 inline-flex items-center justify-center rounded-md hover:bg-accent">
            <MoreHorizontal className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem render={<Link href={`/crm/sequences/${sequence.id}`} />}>
              View
            </DropdownMenuItem>
            <DropdownMenuItem render={<Link href={`/crm/sequences/${sequence.id}/edit`} />}>
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDelete} variant="destructive">
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];

export function SequenceTable({ sequences }: { sequences: Sequence[] }) {
  return <DataTable columns={columns} data={sequences} />;
}
