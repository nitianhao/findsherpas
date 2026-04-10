import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Payment canceled",
};

export default async function StripeCancelPage({
  searchParams,
}: {
  searchParams: Promise<{ tier?: string }>;
}) {
  const { tier } = await searchParams;

  return (
    <div className="py-10">
      <Card className="mx-auto max-w-2xl">
        <CardHeader>
          <CardTitle>Payment canceled</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            No worries—nothing was charged. You can try again, pick a different
            tier, or contact me if you’d rather scope it first.
          </p>
          <div className="rounded-2xl bg-muted p-4 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Tier:</span>{" "}
            {tier ?? "—"}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild>
              <Link href="/pricing">Back to pricing</Link>
            </Button>
            <Button asChild variant="outline">
              <a href="mailto:michal.pekarcik@gmail.com?subject=Find%20Sherpas%20audit%20-%20question">
                Contact
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

