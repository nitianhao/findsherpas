import Link from "next/link";
import { ArrowRight } from "lucide-react";
export function ContactBand() {
  return (
    <section className="fs-contact-band fs-section">
      <h2>
        What should your
        <br />
        search do better?
      </h2>
      <div>
        <p>
          Tell us about your store, your search platform and what you want to
          improve. We will work out where it makes sense to start.
        </p>
        <Link className="fs-button fs-button-light" href="/contact">
          Discuss your search <ArrowRight size={21} aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}
