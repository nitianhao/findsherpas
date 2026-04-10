"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Company } from "@/lib/crm/types";
import { DataTable } from "@/components/crm/shared/data-table";
import { StatusBadge } from "@/components/crm/shared/status-badge";
import { TagBadge } from "@/components/crm/tags/tag-badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/crm/ui/dropdown-menu";
import { MoreHorizontal, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

const columns: ColumnDef<Company>[] = [
  {
    accessorKey: "name",
    header: "Company",
    cell: ({ row }) => (
      <Link href={`/crm/companies/${row.original.id}`} className="font-medium hover:underline">
        {row.getValue("name")}
      </Link>
    ),
  },
  {
    accessorKey: "website",
    header: "Website",
    cell: ({ row }) => {
      const url = row.getValue("website") as string | null;
      if (!url) return <span className="text-muted-foreground">-</span>;
      return (
        <a href={url.startsWith("http") ? url : `https://${url}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm text-blue-600 hover:underline">
          {url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
          <ExternalLink className="h-3 w-3" />
        </a>
      );
    },
  },
  {
    accessorKey: "platform",
    header: "Platform",
    cell: ({ row }) => row.getValue("platform") || <span className="text-muted-foreground">-</span>,
  },
  {
    accessorKey: "search_solution",
    header: "Search",
    cell: ({ row }) => row.getValue("search_solution") || <span className="text-muted-foreground">-</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.getValue("status")} />,
  },
  {
    id: "tags",
    header: "Tags",
    cell: ({ row }) => {
      const tags = row.original.tags || [];
      if (tags.length === 0) return <span className="text-muted-foreground">-</span>;
      return (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <TagBadge key={tag.id} name={tag.name} color={tag.color} />
          ))}
        </div>
      );
    },
  },
  {
    id: "actions",
    cell: function ActionsCell({ row }) {
      const router = useRouter();
      const company = row.original;

      async function handleDelete() {
        if (!confirm("Delete this company? This will also delete all associated contacts.")) return;
        const res = await fetch(`/api/crm/companies/${company.id}`, { method: "DELETE" });
        if (res.ok) {
          toast.success("Company deleted");
          router.refresh();
        } else {
          toast.error("Failed to delete company");
        }
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger className="h-8 w-8 p-0 inline-flex items-center justify-center rounded-md hover:bg-accent">
            <MoreHorizontal className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem render={<Link href={`/crm/companies/${company.id}`} />}>
              View
            </DropdownMenuItem>
            <DropdownMenuItem render={<Link href={`/crm/companies/${company.id}/edit`} />}>
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

export function CompanyTable({ companies }: { companies: Company[] }) {
  return <DataTable columns={columns} data={companies} />;
}
