import { CrmSidebar } from "@/components/crm/layout/sidebar";
import { Toaster } from "@/components/crm/ui/sonner";

export default function CrmLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <CrmSidebar />
      <main className="pl-64">
        <div className="mx-auto max-w-6xl px-6 py-8 sm:px-8">{children}</div>
      </main>
      <Toaster />
    </>
  );
}
