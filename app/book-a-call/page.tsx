import type { Metadata } from "next";

import { ContactForm } from "@/components/site/contact-form";

export const metadata: Metadata = {
  title: "Book a call",
  description:
    "Tell us about your search challenges and we'll suggest the smallest audit that gets you to a clear next step.",
};

export default function BookACallPage() {
  return (
    <div className="py-10">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Book a call
        </h1>
        <p className="mt-3 text-muted-foreground">
          Tell us what you&apos;re working on and we&apos;ll suggest the
          smallest audit that gets you to a clear next step.
        </p>
      </div>
      <div className="mt-8 max-w-2xl">
        <ContactForm />
      </div>
      <p className="mt-4 max-w-2xl text-xs text-muted-foreground">
        No spam. Reply within 1&ndash;2 business days.
      </p>
    </div>
  );
}
