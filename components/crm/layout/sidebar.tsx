"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import {
  LayoutDashboard,
  Building2,
  Users,
  Mail,
  CalendarCheck,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/crm/dashboard", icon: LayoutDashboard },
  { name: "Companies", href: "/crm/companies", icon: Building2 },
  { name: "Contacts", href: "/crm/contacts", icon: Users },
  { name: "Sequences", href: "/crm/sequences", icon: Mail },
  { name: "Today's Tasks", href: "/crm/tasks", icon: CalendarCheck },
  { name: "Settings", href: "/crm/settings", icon: Settings },
];

export function CrmSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-border/50 bg-background">
      <div className="flex h-14 items-center border-b border-border/50 px-6">
        <Link href="/crm/dashboard" className="flex items-center gap-2.5">
          <Image src="/logo.svg" alt="Find Sherpas" width={28} height={28} className="rounded-lg" />
          <span className="text-sm font-semibold tracking-tight">Find Sherpas</span>
        </Link>
      </div>
      <nav className="flex flex-col gap-0.5 p-3">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all duration-200",
                isActive
                  ? "bg-accent text-primary"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-4 w-4", isActive && "text-primary")} />
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="absolute bottom-0 left-0 right-0 border-t border-border/50 p-4">
        <p className="text-[11px] text-muted-foreground">findsherpas.com</p>
        <p className="text-[11px] text-muted-foreground/60">Search audit & consultancy</p>
      </div>
    </aside>
  );
}
