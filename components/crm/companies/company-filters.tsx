"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Input } from "@/components/crm/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/crm/ui/select";
import { COMPANY_STATUSES, PLATFORMS } from "@/lib/crm/constants";
import { useCallback, useEffect, useState } from "react";

export function CompanyFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") || "");

  const updateParams = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value && value !== "all") {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("offset");
      router.push(`/crm/companies?${params.toString()}`);
    },
    [router, searchParams]
  );

  useEffect(() => {
    const timeout = setTimeout(() => {
      updateParams("search", search);
    }, 300);
    return () => clearTimeout(timeout);
  }, [search, updateParams]);

  return (
    <div className="flex items-center gap-4">
      <Input
        placeholder="Search companies..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />
      <Select
        value={searchParams.get("status") || "all"}
        onValueChange={(value) => updateParams("status", value ?? "all")}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {COMPANY_STATUSES.map((s) => (
            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={searchParams.get("platform") || "all"}
        onValueChange={(value) => updateParams("platform", value ?? "all")}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="All platforms" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All platforms</SelectItem>
          {PLATFORMS.map((p) => (
            <SelectItem key={p} value={p}>{p}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
