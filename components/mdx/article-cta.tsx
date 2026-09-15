import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function ArticleCtaMidway() {
  return (
    <aside className="fs-article-cta">
      <h2>Try it on your own search.</h2>
      <p>
        Use the self-assessment to look at one of your important queries and the
        results it returns.
      </p>
      <Link href="/search-check" className="fs-text-link">
        Run the search self-assessment{" "}
        <ArrowRight size={20} aria-hidden="true" />
      </Link>
    </aside>
  );
}

export function ArticleCtaClosing() {
  return (
    <aside className="fs-article-cta fs-article-cta-closing">
      <h2>What should your search do better?</h2>
      <p>
        We help ecommerce teams connect search data, relevance and the customer
        experience. Tell us about your platform and what you want to improve.
      </p>
      <Link href="/contact" className="fs-button fs-button-light">
        Discuss your search <ArrowRight size={20} aria-hidden="true" />
      </Link>
    </aside>
  );
}
