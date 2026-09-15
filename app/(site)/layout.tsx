import { Hanken_Grotesk } from "next/font/google";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteNav } from "@/components/site/site-nav";
import { AnalyticsConsent } from "@/components/site/analytics-consent";
import "./site.css";

const hanken = Hanken_Grotesk({
  subsets: ["latin", "latin-ext"],
  variable: "--font-site",
  display: "swap",
});

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
