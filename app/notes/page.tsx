import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search notes — Find Sherpas",
  description:
    "Short observations about internal search systems, relevance behavior, and recurring patterns seen while diagnosing search.",
};

const notes = [
  {
    title: "Why synonym lists rarely fix search problems",
    teaser:
      "Synonyms map strings to strings. They don't address why the system misunderstood the query in the first place — and they often mask deeper indexing or interpretation gaps.",
    href: null,
  },
  {
    title: "Why click-through rate can mislead search evaluation",
    teaser:
      "High click-through on a query doesn't mean the results were good. It may mean users clicked because nothing better was visible, or because the first result was familiar regardless of relevance.",
    href: null,
  },
  {
    title: "Compound queries break more search systems than teams realize",
    teaser:
      "Most search engines treat compound queries as unstructured text. \"waterproof hiking jacket men size L\" is a structured request — but few systems decompose it that way.",
    href: null,
  },
  {
    title: "Merchandising rules often distort relevance",
    teaser:
      "Boosting rules and pinned positions accumulate over time. Each change is local and reasonable. The cumulative effect is a ranking system that no longer reflects user intent.",
    href: null,
  },
];

export default function NotesPage() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="pb-12 pt-16 sm:pb-16 sm:pt-24 lg:pt-32">
        <div className="mx-auto max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
            Notes
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Search notes
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
            Short observations about internal search systems, relevance
            behavior, and recurring patterns seen while diagnosing search.
          </p>
        </div>
      </section>

      {/* ── Notes grid ── */}
      <section className="pb-20 sm:pb-28">
        <div className="mx-auto max-w-3xl">
          <div className="space-y-px divide-y divide-border/40">
            {notes.map((note) => (
              <div key={note.title} className="py-7">
                <h2 className="text-base font-semibold tracking-tight text-foreground">
                  {note.href ? (
                    <a href={note.href} className="hover:text-primary hover:underline">
                      {note.title}
                    </a>
                  ) : (
                    note.title
                  )}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {note.teaser}
                </p>
                {!note.href && (
                  <p className="mt-2 text-xs text-muted-foreground/40">
                    Full note coming soon
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
