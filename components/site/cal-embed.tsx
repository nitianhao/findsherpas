import Link from "next/link";

import { Button } from "@/components/ui/button";

const CAL_URL = "https://cal.eu/michal-pekarcik-r6j8fb";

export function CalEmbed() {
  return (
    <>
      {/* Mobile: link out instead of embedding */}
      <div className="sm:hidden rounded-xl border border-gray-200 bg-gray-50 p-6 text-center">
        <p className="text-sm text-muted-foreground">
          Booking works better in the full calendar view on mobile.
        </p>
        <div className="mt-4">
          <Button asChild size="lg" className="w-full font-semibold">
            <a href={CAL_URL} target="_blank" rel="noopener noreferrer">
              Open booking calendar
            </a>
          </Button>
        </div>
      </div>

      {/* sm+: embedded iframe */}
      <div className="hidden sm:block">
        <iframe
          src={`${CAL_URL}?embed=true&theme=light`}
          width="100%"
          height="700"
          frameBorder="0"
          title="Book an intro call"
          style={{ border: "none", minHeight: "700px" }}
        />
      </div>
    </>
  );
}
