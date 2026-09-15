import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { FocusMark } from "./focus-mark";
import { AnalyticsSettingsButton } from "./analytics-consent";

export function SiteFooter() {
  return (
    <footer className="fs-footer">
      <div className="fs-footer-top">
        <div className="fs-footer-brand">
          <Link href="/" className="fs-wordmark">
            find sherpas
            <FocusMark />
          </Link>
          <p>
            On-site search, understood.
            <br />A boutique search optimization agency.
          </p>
        </div>
        <nav aria-labelledby="footer-company">
          <h2 id="footer-company">Company</h2>
          <Link href="/expertise">What we do</Link>
          <Link href="/approach">How we work</Link>
          <Link href="/about">About</Link>
        </nav>
        <nav aria-labelledby="footer-resources">
          <h2 id="footer-resources">Resources</h2>
          <Link href="/resources">All resources</Link>
          <Link href="/blog">Articles</Link>
          <Link href="/search-check">Search self-assessment</Link>
          <Link href="/frameworks/search-failure-modes">Search failure modes</Link>
          <Link href="/frameworks/query-interpretation">Query interpretation</Link>
        </nav>
        <div className="fs-footer-contact">
          <Link href="/contact">
            Discuss your search <ArrowUpRight size={18} aria-hidden="true" />
          </Link>
          <a href="mailto:michal@findsherpas.com">michal@findsherpas.com</a>
        </div>
      </div>
      <div className="fs-footer-bottom">
        <span>© {new Date().getFullYear()} Find Sherpas</span>
        <span>For ecommerce teams across Europe &amp; the UK.</span>
        <div className="fs-footer-legal">
          <Link href="/privacy">Privacy</Link>
          <AnalyticsSettingsButton />
        </div>
      </div>
    </footer>
  );
}
