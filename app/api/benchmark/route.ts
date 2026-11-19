import { NextResponse } from "next/server";
import { adminDb } from "@/lib/crm/instant-db";

export const dynamic = "force-dynamic";

interface BenchmarkScan {
  id: string;
  vertical: string;
  country: string;
  overall_score: string;
  capabilities: string;
  proof_cards: string;
  probe_count: number;
  scanned_at: string;
}

interface CapabilityCount {
  pass: number;
  partial: number;
  fail: number;
}

interface ProofCard {
  probe_type: string;
  query: string;
  result_count: number;
  control_query: string | null;
  control_count: number | null;
  score_reason: string;
  vertical: string;
  country: string;
}

export async function GET() {
  try {
    const data = await adminDb.query({ benchmarkScans: {} });
    const scans = (data.benchmarkScans || []) as BenchmarkScan[];

    if (scans.length === 0) {
      return NextResponse.json({
        total_stores: 0,
        capability_distribution: {},
        proof_cards: [],
        by_vertical: {},
        by_country: {},
      });
    }

    const capabilityDistribution: Record<string, CapabilityCount> = {};
    const proofCards: ProofCard[] = [];
    const byVertical: Record<string, { count: number; pass: number; fail: number }> = {};
    const byCountry: Record<string, { count: number; pass: number; fail: number }> = {};

    for (const scan of scans) {
      const vertical = scan.vertical || "unknown";
      const country = scan.country || "unknown";
      const overallScore = scan.overall_score || "error";

      // Count by vertical
      if (!byVertical[vertical]) {
        byVertical[vertical] = { count: 0, pass: 0, fail: 0 };
      }
      byVertical[vertical].count++;
      if (overallScore === "pass") byVertical[vertical].pass++;
      if (overallScore === "fail") byVertical[vertical].fail++;

      // Count by country
      if (!byCountry[country]) {
        byCountry[country] = { count: 0, pass: 0, fail: 0 };
      }
      byCountry[country].count++;
      if (overallScore === "pass") byCountry[country].pass++;
      if (overallScore === "fail") byCountry[country].fail++;

      // Aggregate capability scores
      try {
        const caps = JSON.parse(scan.capabilities || "{}");
        for (const [capName, capData] of Object.entries(caps)) {
          if (!capabilityDistribution[capName]) {
            capabilityDistribution[capName] = { pass: 0, partial: 0, fail: 0 };
          }
          const score = (capData as { score: string }).score || "error";
          if (score === "pass") capabilityDistribution[capName].pass++;
          else if (score === "partial") capabilityDistribution[capName].partial++;
          else if (score === "fail") capabilityDistribution[capName].fail++;
        }
      } catch {
        // Skip malformed capabilities
      }

      // Collect proof cards
      try {
        const cards = JSON.parse(scan.proof_cards || "[]") as Omit<ProofCard, "vertical" | "country">[];
        for (const card of cards) {
          proofCards.push({
            ...card,
            vertical,
            country,
          });
        }
      } catch {
        // Skip malformed proof cards
      }
    }

    // Sort proof cards by impact (control_count - result_count)
    proofCards.sort((a, b) => {
      const impactA = (a.control_count || 0) - (a.result_count || 0);
      const impactB = (b.control_count || 0) - (b.result_count || 0);
      return impactB - impactA;
    });

    return NextResponse.json({
      total_stores: scans.length,
      capability_distribution: capabilityDistribution,
      proof_cards: proofCards.slice(0, 30),
      by_vertical: byVertical,
      by_country: byCountry,
    });
  } catch (error) {
    console.error("Failed to fetch benchmark data:", error);
    return NextResponse.json(
      { error: "Failed to fetch benchmark data" },
      { status: 500 }
    );
  }
}
