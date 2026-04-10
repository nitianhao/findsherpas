import type { Metadata } from "next";
import { Calendar, MessageSquare, Mail } from "lucide-react";

import { CalEmbed } from "@/components/site/cal-embed";
import { ReachOutForm } from "@/components/site/reach-out-form";

export const metadata: Metadata = {
  title: { absolute: "Book a call | Find Sherpas" },
  description:
    "Book a short intro call to discuss your internal search system and whether a diagnostic audit makes sense.",
  alternates: { canonical: "https://findsherpas.com/book-a-call" },
};

export default function BookACallPage() {
  return (
    <div className="py-6 sm:py-10">
      {/* Header */}
      <div className="max-w-2xl">
        <div className="flex items-center gap-2.5">
          <Calendar size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Book an intro call
          </h1>
        </div>
        <p className="mt-3 max-w-xl text-muted-foreground">
          A short call to discuss your search system and whether a diagnostic
          makes sense. No commitment required.
        </p>
      </div>

      {/* What we'll cover */}
      <div className="mt-6 sm:mt-10 max-w-[600px]">
        <h2 className="text-base font-semibold text-gray-900">
          What we&apos;ll cover
        </h2>
        <ul className="mt-3 space-y-2 text-sm text-gray-700">
          <li className="flex items-baseline gap-2">
            <span className="text-gray-400">&bull;</span>
            A quick overview of your search setup
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-gray-400">&bull;</span>
            Examples of queries or results that seem broken
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-gray-400">&bull;</span>
            Whether a diagnostic review would actually be useful
          </li>
        </ul>
        <p className="mt-4 text-sm text-gray-600">
          Most calls end with a few concrete observations you can take back to your team.
        </p>
      </div>

      {/* Who this call is for */}
      <div className="mt-6 sm:mt-10 max-w-[600px]">
        <h2 className="text-base font-semibold text-gray-900">
          Who this call is for
        </h2>
        <div className="mt-4 grid gap-6 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Good fit</p>
            <ul className="mt-2 space-y-2 text-sm text-gray-700">
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Ecommerce or marketplace sites with large catalogs</li>
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Teams trying to improve search relevance or ranking</li>
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Search systems with synonyms, boosting, or merchandising rules</li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Probably not a fit</p>
            <ul className="mt-2 space-y-2 text-sm text-gray-700">
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Very small catalogs where search plays a minor role</li>
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Sites with very low search usage</li>
              <li className="flex items-baseline gap-2"><span className="text-gray-400">&bull;</span>Teams looking for ongoing implementation work</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Calendar embed */}
      <div className="mt-6 sm:mt-8">
        <CalEmbed />
      </div>

      {/* Divider */}
      <div className="my-8 sm:my-16 border-t border-border/40" />

      {/* Alternative contact */}
      <div className="max-w-[600px]">
        <div className="flex items-center gap-2.5">
          <MessageSquare size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">Prefer to reach out first?</h2>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          If you&apos;d rather send a short message before booking a call, feel
          free to use the form below or email directly.
        </p>

        <div className="mt-8">
          <ReachOutForm />
        </div>

        {/* Direct email */}
        <div className="mt-8 border-t border-border/40 pt-6">
          <div className="flex items-center gap-2">
            <Mail size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
            <p className="text-sm text-muted-foreground">Or email directly</p>
          </div>
          <a
            href="mailto:contact@findsherpas.com"
            className="mt-1 inline-block text-sm font-medium text-foreground underline-offset-4 hover:underline"
          >
            contact@findsherpas.com
          </a>
        </div>
      </div>
    </div>
  );
}
