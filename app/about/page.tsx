import type { Metadata } from "next";

import { Badge } from "@/components/ui/badge";
import { LANGUAGES_EXCLUDED, SUPPORTED_LANGUAGES } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description: "About Find Sherpas.",
};

export default function AboutPage() {
  return (
    <div className="py-10">
      <h1 className="text-3xl font-semibold tracking-tight">About</h1>
      <p className="mt-3 max-w-2xl text-muted-foreground">
        This page will be filled with content later.
      </p>

      <section className="mt-12">
        <h2 className="text-xl font-semibold tracking-tight">Languages</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          I work in all European languages except{" "}
          {LANGUAGES_EXCLUDED.join(", ")}.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <Badge key={lang} variant="secondary">
              {lang}
            </Badge>
          ))}
        </div>
      </section>
    </div>
  );
}

