import { Badge } from "@/components/crm/ui/badge";
import { COMPANY_STATUSES, CONTACT_STATUSES, ENROLLMENT_STATUSES, EVENT_STATUSES } from "@/lib/crm/constants";

const ALL_STATUSES = [...COMPANY_STATUSES, ...CONTACT_STATUSES, ...ENROLLMENT_STATUSES, ...EVENT_STATUSES];

export function StatusBadge({ status }: { status: string }) {
  const config = ALL_STATUSES.find((s) => s.value === status);
  if (!config) return <Badge variant="outline">{status}</Badge>;
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}
