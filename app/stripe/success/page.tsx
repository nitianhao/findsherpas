import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Payment successful",
};

export default async function StripeSuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ tier?: string; session_id?: string }>;
}) {
  const { tier, session_id } = await searchParams;

  return (
    <div className="py-10">
      <Card className="mx-auto max-w-2xl">
        <CardHeader>
          <CardTitle>Payment successful</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Thanks—your payment went through. I’ll email you shortly with next
            steps and a short intake checklist.
          </p>
          <div className="rounded-2xl bg-muted p-4 text-xs text-muted-foreground">
            <div>
              <span className="font-medium text-foreground">Tier:</span>{" "}
              {tier ?? "—"}
            </div>
            <div>
              <span className="font-medium text-foreground">Session:</span>{" "}
              {session_id ?? "—"}
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild>
              <Link href="/">Back to home</Link>
            </Button>
            <Button asChild variant="outline">
              <a href="mailto:michal.pekarcik@gmail.com?subject=Find%20Sherpas%20audit%20-%20next%20steps">
                Email me
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

