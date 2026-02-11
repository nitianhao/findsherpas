export type TierId = "starter" | "growth" | "enterprise";

export type Tier = {
  id: TierId;
  name: string;
  priceLabel: string;
  bestFor: string;
  delivery: string;
  includes: string[];
};

export const tiers: Tier[] = [
  {
    id: "starter",
    name: "Starter Audit",
    priceLabel: "€990",
    bestFor: "A fast, structured diagnosis and a clear fix list.",
    delivery: "5–7 business days",
    includes: [
      "Search UX audit (journeys, SERP, filters, zero-results)",
      "Top issue list (prioritized)",
      "Quick wins + recommended experiments",
      "60-min walkthrough call",
    ],
  },
  {
    id: "growth",
    name: "Growth Audit",
    priceLabel: "€2,490",
    bestFor: "Teams ready to tune relevance and measure progress.",
    delivery: "10–14 business days",
    includes: [
      "Everything in Starter",
      "Relevance audit (queries, synonyms, facets, ranking signals)",
      "Search analytics review (events, funnels, dashboards)",
      "Measurement plan + KPI definitions",
      "2× 60-min working sessions",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise Audit",
    priceLabel: "Custom",
    bestFor: "Complex catalogs or marketplaces needing deep diagnosis.",
    delivery: "2–4 weeks",
    includes: [
      "Everything in Growth",
      "Query set design + evaluation approach",
      "Advanced failure modes (coverage gaps, long-tail, merch rules)",
      "Implementation support (handover + review)",
      "Stakeholder workshop",
    ],
  },
];

export type ComparisonRow = {
  label: string;
  starter: boolean;
  growth: boolean;
  enterprise: boolean;
};

export const comparisonRows: ComparisonRow[] = [
  { label: "Search UX audit", starter: true, growth: true, enterprise: true },
  { label: "Prioritized issue list", starter: true, growth: true, enterprise: true },
  { label: "Recommended experiments", starter: true, growth: true, enterprise: true },
  { label: "Relevance audit & tuning plan", starter: false, growth: true, enterprise: true },
  { label: "Search analytics audit", starter: false, growth: true, enterprise: true },
  { label: "KPI + measurement design", starter: false, growth: true, enterprise: true },
  { label: "Query evaluation framework", starter: false, growth: false, enterprise: true },
  { label: "Implementation support", starter: false, growth: false, enterprise: true },
  { label: "Workshop", starter: false, growth: false, enterprise: true },
];

export const tierStripePriceEnv: Record<TierId, string> = {
  starter: "STRIPE_PRICE_STARTER",
  growth: "STRIPE_PRICE_GROWTH",
  enterprise: "STRIPE_PRICE_ENTERPRISE",
};

