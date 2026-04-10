"use client";

import { ColumnDef } from "@tanstack/react-table";
import type { ContactSequence } from "@/lib/crm/types";
import { DataTable } from "@/components/crm/shared/data-table";
import { StatusBadge } from "@/components/crm/shared/status-badge";
import { Button } from "@/components/crm/ui/button";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pause, Play } from "lucide-react";
import Link from "next/link";

function ActionsCell({ enrollment }: { enrollment: ContactSequence }) {
  const router = useRouter();

  async function handlePauseResume() {
    const action = enrollment.status === "paused" ? "resume" : "pause";
    const res = await fetch(`/api/crm/sequences/enroll/${enrollment.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (res.ok) {
      toast.success(action === "pause" ? "Enrollment paused" : "Enrollment resumed");
      router.refresh();
    } else {
      toast.error(`Failed to ${action} enrollment`);
    }
  }

  if (enrollment.status !== "active" && enrollment.status !== "paused") {
    return null;
  }

  return (
    <Button variant="ghost" size="sm" onClick={handlePauseResume}>
      {enrollment.status === "paused" ? (
        <>
          <Play className="mr-1 h-3 w-3" />
          Resume
        </>
      ) : (
        <>
          <Pause className="mr-1 h-3 w-3" />
          Pause
        </>
      )}
    </Button>
  );
}

const columns: ColumnDef<ContactSequence>[] = [
  {
    accessorKey: "contact_name",
    header: "Contact",
    cell: ({ row }) => (
      <Link
        href={`/crm/contacts/${row.original.contact_id}`}
        className="font-medium hover:underline"
      >
        {row.original.contact_name}
      </Link>
    ),
  },
  {
    accessorKey: "contact_email",
    header: "Email",
  },
  {
    accessorKey: "company_name",
    header: "Company",
    cell: ({ row }) => row.original.company_name || "--",
  },
  {
    accessorKey: "current_step",
    header: "Current Step",
    cell: ({ row }) => `Step ${row.original.current_step}`,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    id: "actions",
    header: "Actions",
    cell: function ActionsCellWrapper({ row }) {
      return <ActionsCell enrollment={row.original} />;
    },
  },
];

export function EnrollmentTable({
  enrollments,
}: {
  enrollments: ContactSequence[];
}) {
  return <DataTable columns={columns} data={enrollments} />;
}
