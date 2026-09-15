import type { Metadata } from "next";

// Case studies remain drafts until publication evidence is approved.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function CaseStudyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="fs-legacy">{children}</div>;
}
