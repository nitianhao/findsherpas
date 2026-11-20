import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowRight, CheckCircle2, AlertCircle, MinusCircle, ExternalLink } from "lucide-react";
import { adminDb } from "@/lib/crm/instant-db";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  
  return {
    title: "Your Search Teardown Report | Find Sherpas",
    description: "Private search capability analysis for your store.",
    robots: {
      index: false,
      follow: false,
      noarchive: true,
      nosnippet: true,
    },
    openGraph: {
      title: "Your Search Teardown Report",
      description: "Private search capability analysis",
    },
  };
}

interface TeardownScan {
  id: string;
  domain: string;
  site_name: string | null;
  vertical: string | null;
  country: string | null;
  overall_score: string;
  capabilities: string;
  probes: string;
  blocked: boolean;
  scanned_at: string;
}

interface AuditRequest {
  id: string;
  store_url: string;
  name: string;
  problem_queries: string | null;
  report_slug: string;
  teardownScan: TeardownScan | null;
}

async function getReportBySlug(slug: string): Promise<AuditRequest | null> {
  try {
    const data = await adminDb.query({
      auditRequests: {
        $: { where: { report_slug: slug } },
        teardownScan: {},
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const request = (data.auditRequests as any[])[0];
    if (!request) return null;

    return {
      id: request.id,
      store_url: request.store_url,
      name: request.name,
      problem_queries: request.problem_queries,
      report_slug: request.report_slug,
      teardownScan: request.teardownScan || null,
    };
  } catch {
    return null;
  }
}

const CAPABILITY_LABELS: Record<string, string> = {
  basic_retrieval: "Basic retrieval",
  typo_tolerance: "Typo tolerance",
  language_understanding: "Language understanding",
  locale_handling: "Locale & format handling",
  compound_handling: "Compound word handling",
  constraint_handling: "Constraint handling",
  brand_model_search: "Brand & model search",
  coverage_ranking: "Coverage & ranking",
  zero_result_handling: "Zero-result handling",
};

const PROBE_TYPE_LABELS: Record<string, string> = {
  exact_product_name: "Exact product name",
  category_term: "Category term",
  typo: "Typo",
  synonym: "Synonym",
  plural_singular: "Plural/singular",
  diacritics: "Diacritics",
  format_variant: "Format variant",
  abbreviation: "Abbreviation",
  compound_split: "Compound split",
  merged_words: "Merged words",
  constraint_query: "Constraint",
  price_constraint: "Price constraint",
  brand_search: "Brand search",
  sku_search: "SKU search",
  coverage_check: "Coverage",
  ranking_check: "Ranking",
  zero_result_check: "Zero-result",
  control_query: "Control",
};

function ScoreIcon({ score }: { score: string }) {
  if (score === "pass") {
    return <CheckCircle2 className="h-5 w-5 text-green-600" />;
  }
  if (score === "partial") {
    return <MinusCircle className="h-5 w-5 text-yellow-600" />;
  }
  if (score === "fail") {
    return <AlertCircle className="h-5 w-5 text-red-600" />;
  }
  return <MinusCircle className="h-5 w-5 text-gray-400" />;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default async function TeardownReportPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const report = await getReportBySlug(slug);

  if (!report || !report.teardownScan) {
    notFound();
  }

  const scan = report.teardownScan;
  let capabilities: Record<string, { score: string; summary: string }> = {};
  let probes: Array<{
    probe_type: string;
    query: string;
    control_query: string | null;
    result_count: number;
    control_count: number | null;
    score: string;
    score_reason: string;
    results: Array<{ title: string; price: string | null }>;
  }> = [];

  try {
    capabilities = JSON.parse(scan.capabilities);
  } catch {}

  try {
    probes = JSON.parse(scan.probes);
  } catch {}

  const failedProbes = probes.filter((p) => p.score === "fail");
  const passedProbes = probes.filter((p) => p.score === "pass");

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b bg-gray-50 px-6 py-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-sm text-gray-500 mb-2">
            Private teardown report for {report.name}
          </p>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Search Teardown: {scan.domain}
          </h1>
          <div className="flex flex-wrap gap-4 text-sm text-gray-600">
            <span>Scanned {formatDate(scan.scanned_at)}</span>
            {scan.vertical && <span>• {scan.vertical}</span>}
            {scan.country && <span>• {scan.country}</span>}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-10">
        {/* Overall Score */}
        <section className="mb-12">
          <div className="flex items-center gap-4 mb-6">
            <div
              className={`text-5xl font-bold ${
                scan.overall_score === "pass"
                  ? "text-green-600"
                  : scan.overall_score === "fail"
                  ? "text-red-600"
                  : "text-yellow-600"
              }`}
            >
              {scan.overall_score === "pass"
                ? "Good"
                : scan.overall_score === "fail"
                ? "Issues Found"
                : "Partial"}
            </div>
          </div>
          <p className="text-gray-600 max-w-2xl">
            {scan.overall_score === "pass"
              ? "Your search handles the core capabilities well. There may be edge cases to improve, but the fundamentals are solid."
              : scan.overall_score === "fail"
              ? "We found significant gaps in your search capabilities. Shoppers searching with typos, synonyms, or constraints may hit dead ends."
              : "Your search handles some capabilities well but has gaps in others. Review the details below."}
          </p>
        </section>

        {/* Capability Scores */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold mb-6">Capability Breakdown</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {Object.entries(capabilities).map(([name, data]) => (
              <div
                key={name}
                className="flex items-center gap-3 p-4 border rounded-lg"
              >
                <ScoreIcon score={data.score} />
                <div className="flex-1">
                  <div className="font-medium">
                    {CAPABILITY_LABELS[name] || name}
                  </div>
                  <div className="text-sm text-gray-500">{data.summary}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Failed Probes */}
        {failedProbes.length > 0 && (
          <section className="mb-12">
            <h2 className="text-xl font-semibold mb-6">
              Issues Found ({failedProbes.length})
            </h2>
            <div className="space-y-6">
              {failedProbes.map((probe, index) => (
                <div
                  key={index}
                  className="border border-red-200 rounded-lg p-5 bg-red-50"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="text-sm font-medium text-red-800">
                        {PROBE_TYPE_LABELS[probe.probe_type] || probe.probe_type}
                      </span>
                    </div>
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-red-700">Query:</span>
                      <code className="bg-white px-2 py-1 rounded text-sm">
                        {probe.query}
                      </code>
                      <span className="text-sm text-red-600">
                        → {probe.result_count} results
                      </span>
                    </div>
                    {probe.control_query && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-green-700">Control:</span>
                        <code className="bg-white px-2 py-1 rounded text-sm">
                          {probe.control_query}
                        </code>
                        <span className="text-sm text-green-600">
                          → {probe.control_count} results
                        </span>
                      </div>
                    )}
                    <p className="text-sm text-gray-700">{probe.score_reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Passed Probes */}
        {passedProbes.length > 0 && (
          <section className="mb-12">
            <h2 className="text-xl font-semibold mb-6">
              Working Well ({passedProbes.length})
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {passedProbes.map((probe, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 border border-green-200 rounded-lg bg-green-50"
                >
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-green-800 truncate">
                      {PROBE_TYPE_LABELS[probe.probe_type] || probe.probe_type}
                    </div>
                    <div className="text-xs text-green-600 truncate">
                      "{probe.query}"
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* CTA */}
        <section className="border-t pt-10">
          <h2 className="text-xl font-semibold mb-4">
            Want to fix these issues?
          </h2>
          <p className="text-gray-600 mb-6 max-w-2xl">
            We can help you understand what's causing these failures and
            prioritize the fixes that will have the biggest impact on your
            customers. Reply to the email that sent you this report, or get in
            touch directly.
          </p>
          <Link
            href="/contact"
            className="inline-flex items-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-800 transition-colors"
          >
            Discuss your search
            <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t bg-gray-50 px-6 py-8 mt-12">
        <div className="mx-auto max-w-4xl text-center text-sm text-gray-500">
          <p className="mb-2">
            This report is private and not indexed by search engines.
          </p>
          <p>
            <Link href="/" className="text-gray-700 hover:underline">
              Find Sherpas
            </Link>{" "}
            — On-site search optimization for ecommerce
          </p>
        </div>
      </footer>
    </div>
  );
}
