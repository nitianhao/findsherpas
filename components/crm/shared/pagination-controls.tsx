import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { cn } from "@/lib/utils";

interface PaginationControlsProps {
  basePath: string;
  currentPage: number;
  pageSize: number;
  total: number;
  searchParams?: Record<string, string | undefined>;
}

function pageHref(basePath: string, searchParams: Record<string, string | undefined>, page: number) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (value && key !== "page" && key !== "offset") params.set(key, value);
  }
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `${basePath}?${query}` : basePath;
}

export function PaginationControls({
  basePath,
  currentPage,
  pageSize,
  total,
  searchParams = {},
}: PaginationControlsProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(currentPage, 1), totalPages);
  const start = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end = Math.min(safePage * pageSize, total);

  return (
    <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        Showing {start}-{end} of {total} - Page {safePage} of {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <Link
          href={pageHref(basePath, searchParams, safePage - 1)}
          aria-disabled={safePage <= 1}
          className={cn(
            buttonVariants({ variant: "outline", size: "sm" }),
            safePage <= 1 && "pointer-events-none opacity-50"
          )}
        >
          Previous
        </Link>
        <Link
          href={pageHref(basePath, searchParams, safePage + 1)}
          aria-disabled={safePage >= totalPages}
          className={cn(
            buttonVariants({ variant: "outline", size: "sm" }),
            safePage >= totalPages && "pointer-events-none opacity-50"
          )}
        >
          Next
        </Link>
      </div>
    </div>
  );
}
