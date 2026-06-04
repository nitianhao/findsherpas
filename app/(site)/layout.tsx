import { SiteFooter } from "@/components/site/site-footer";
import { SiteNav } from "@/components/site/site-nav";
import { ScrollToTop } from "@/components/site/scroll-to-top";

export default function SiteLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="relative min-h-dvh bg-background">
      {/* Brand gradient overlay at the top of every page */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-96 bg-gradient-to-b from-primary/[0.14] via-primary/[0.05] to-transparent"
      />
      <div className="relative">
        <SiteNav />
        <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
          {children}
        </main>
        <SiteFooter />
      </div>
      <ScrollToTop />
    </div>
  );
}
