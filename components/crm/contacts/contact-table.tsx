"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Contact } from "@/lib/crm/types";
import { DataTable } from "@/components/crm/shared/data-table";
import { StatusBadge } from "@/components/crm/shared/status-badge";
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

const columns: ColumnDef<Contact>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link href={`/crm/contacts/${row.original.id}`} className="font-medium hover:underline">
        {row.getValue("name")}
      </Link>
    ),
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => (
      <span className="text-sm">{row.getValue("email")}</span>
    ),
  },
  {
    accessorKey: "role",
    header: "Role",
    cell: ({ row }) =>
      row.getValue("role") || <span className="text-muted-foreground">-</span>,
  },
  {
    accessorKey: "company_name",
    header: "Company",
    cell: ({ row }) => {
      const companyName = row.original.company_name;
      const companyId = row.original.company_id;
      if (!companyName) return <span className="text-muted-foreground">-</span>;
      return (
        <Link href={`/crm/companies/${companyId}`} className="text-sm text-blue-600 hover:underline">
          {companyName}
        </Link>
      );
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.getValue("status")} />,
  },
  {
    id: "actions",
    cell: function ActionsCell({ row }) {
      const router = useRouter();
      const contact = row.original;

      async function handleDelete() {
        if (!confirm("Delete this contact? This cannot be undone.")) return;
        const res = await fetch(`/api/crm/contacts/${contact.id}`, { method: "DELETE" });
        if (res.ok) {
          toast.success("Contact deleted");
          router.refresh();
        } else {
          toast.error("Failed to delete contact");
        }
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger className="h-8 w-8 p-0 inline-flex items-center justify-center rounded-md hover:bg-accent">
            <MoreHorizontal className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem render={<Link href={`/crm/contacts/${contact.id}`} />}>
              View
            </DropdownMenuItem>
            <DropdownMenuItem render={<Link href={`/crm/contacts/${contact.id}/edit`} />}>
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

export function ContactTable({ contacts }: { contacts: Contact[] }) {
  return <DataTable columns={columns} data={contacts} />;
}
