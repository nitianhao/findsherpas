import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Case studies",
  description:
    "Detailed search case studies are being prepared for publication.",
  alternates: { canonical: "https://findsherpas.com/case-studies" },
};

export default function CaseStudiesPage() {
  return (
    <section className="fs-prose">
      <h1>
        Case studies
        <br />
        are on their way.
      </h1>
      <p>
        We are preparing the work and results we can share publicly. In the
        meantime, explore our approach or tell us about your search.
      </p>
      <Link href="/approach" className="fs-text-link">
        How we work <ArrowRight size={20} aria-hidden="true" />
      </Link>
    </section>
  );
}
