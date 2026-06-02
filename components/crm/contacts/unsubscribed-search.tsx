"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Input } from "@/components/crm/ui/input";
import { useCallback, useEffect, useState } from "react";

export function UnsubscribedSearch() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSearch = searchParams.get("search") || "";
  const [search, setSearch] = useState(currentSearch);

  const updateSearch = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) params.set("search", value);
      else params.delete("search");
      params.delete("page");
      router.push(`/crm/unsubscribed?${params.toString()}`);
    },
    [router, searchParams]
  );

  useEffect(() => {
    if (search === currentSearch) return;
    const timeout = setTimeout(() => updateSearch(search), 300);
    return () => clearTimeout(timeout);
  }, [currentSearch, search, updateSearch]);

  return (
    <Input
      placeholder="Search by name or email..."
      value={search}
      onChange={(e) => setSearch(e.target.value)}
      className="max-w-sm"
    />
  );
}
