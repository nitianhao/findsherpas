import { hanken } from "@/lib/site-font";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteNav } from "@/components/site/site-nav";
import { AnalyticsConsent } from "@/components/site/analytics-consent";
import "./site.css";

export default function SiteLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className={`fs-site ${hanken.variable}`}>
      <a href="#main-content" className="fs-skip-link">
        Skip to content
      </a>
      <SiteNav />
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <SiteFooter />
      <AnalyticsConsent />
    </div>
  );
}
