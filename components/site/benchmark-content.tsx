"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, MinusCircle } from "lucide-react";

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

interface VerticalData {
  count: number;
  pass: number;
  fail: number;
}

interface BenchmarkData {
  total_stores: number;
  capability_distribution: Record<string, CapabilityCount>;
  proof_cards: ProofCard[];
  by_vertical: Record<string, VerticalData>;
  by_country: Record<string, VerticalData>;
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

function CapabilityBar({ name, counts }: { name: string; counts: CapabilityCount }) {
  const total = counts.pass + counts.partial + counts.fail;
  if (total === 0) return null;

  const passPercent = (counts.pass / total) * 100;
  const partialPercent = (counts.partial / total) * 100;
  const failPercent = (counts.fail / total) * 100;

  return (
    <div className="fs-benchmark-capability">
      <div className="fs-benchmark-capability-header">
        <span className="fs-benchmark-capability-name">
          {CAPABILITY_LABELS[name] || name}
        </span>
        <span className="fs-benchmark-capability-stats">
          {counts.pass} pass · {counts.partial} partial · {counts.fail} fail
        </span>
      </div>
      <div className="fs-benchmark-capability-bar">
        {passPercent > 0 && (
          <div
            className="fs-benchmark-bar-pass"
            style={{ width: `${passPercent}%` }}
            title={`${Math.round(passPercent)}% pass`}
          />
        )}
        {partialPercent > 0 && (
          <div
            className="fs-benchmark-bar-partial"
            style={{ width: `${partialPercent}%` }}
            title={`${Math.round(partialPercent)}% partial`}
          />
        )}
        {failPercent > 0 && (
          <div
            className="fs-benchmark-bar-fail"
            style={{ width: `${failPercent}%` }}
            title={`${Math.round(failPercent)}% fail`}
          />
        )}
      </div>
    </div>
  );
}

function ProofCardDisplay({ card }: { card: ProofCard }) {
  return (
    <article className="fs-proof-card">
      <div className="fs-proof-card-header">
        <span className="fs-proof-card-type">
          {PROBE_TYPE_LABELS[card.probe_type] || card.probe_type}
        </span>
        <span className="fs-proof-card-meta">
          {card.vertical} · {card.country}
        </span>
      </div>
      <div className="fs-proof-card-comparison">
        <div className="fs-proof-card-query fs-proof-card-fail">
          <AlertCircle size={16} aria-hidden="true" />
          <span className="fs-proof-card-term">"{card.query}"</span>
          <span className="fs-proof-card-count">
            {card.result_count === 0 ? "0 results" : `${card.result_count} results`}
          </span>
        </div>
        {card.control_query && (
          <div className="fs-proof-card-query fs-proof-card-pass">
            <CheckCircle2 size={16} aria-hidden="true" />
            <span className="fs-proof-card-term">"{card.control_query}"</span>
            <span className="fs-proof-card-count">
              {card.control_count} results
            </span>
          </div>
        )}
      </div>
      <p className="fs-proof-card-reason">{card.score_reason}</p>
    </article>
  );
}

function EmptyState() {
  return (
    <section className="fs-section fs-benchmark-empty">
      <div className="fs-benchmark-empty-content">
        <MinusCircle size={48} className="fs-benchmark-empty-icon" aria-hidden="true" />
        <h3>No benchmark data yet.</h3>
        <p>
          We're building the benchmark from stores across verticals and markets.
          Check back soon—or request a teardown to be among the first.
        </p>
      </div>
    </section>
  );
}

export function BenchmarkContent() {
  const [data, setData] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch("/api/benchmark");
        if (!response.ok) {
          throw new Error("Failed to fetch benchmark data");
        }
        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <section className="fs-section fs-benchmark-loading">
        <p>Loading benchmark data...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="fs-section fs-benchmark-error">
        <p>Could not load benchmark data. Please try again later.</p>
      </section>
    );
  }

  if (!data || data.total_stores === 0) {
    return <EmptyState />;
  }

  const capabilities = Object.entries(data.capability_distribution).sort(
    ([, a], [, b]) => (b.fail + b.partial) - (a.fail + a.partial)
  );

  const verticals = Object.entries(data.by_vertical)
    .filter(([, v]) => v.count >= 1)
    .sort(([, a], [, b]) => b.count - a.count);

  return (
    <>
      <section className="fs-section fs-benchmark-overview">
        <div className="fs-benchmark-stat">
          <span className="fs-benchmark-stat-value">{data.total_stores}</span>
          <span className="fs-benchmark-stat-label">stores tested</span>
        </div>
        <div className="fs-benchmark-stat">
          <span className="fs-benchmark-stat-value">
            {Object.keys(data.by_vertical).length}
          </span>
          <span className="fs-benchmark-stat-label">verticals</span>
        </div>
        <div className="fs-benchmark-stat">
          <span className="fs-benchmark-stat-value">
            {Object.keys(data.by_country).length}
          </span>
          <span className="fs-benchmark-stat-label">countries</span>
        </div>
      </section>

      <section className="fs-section fs-benchmark-capabilities" aria-labelledby="cap-title">
        <h2 id="cap-title">Capability breakdown.</h2>
        <p className="fs-benchmark-capabilities-intro">
          How stores perform across search capability areas. Each bar shows the
          distribution of pass, partial, and fail scores.
        </p>
        <div className="fs-benchmark-capability-list">
          {capabilities.map(([name, counts]) => (
            <CapabilityBar key={name} name={name} counts={counts} />
          ))}
        </div>
      </section>

      {data.proof_cards.length > 0 && (
        <section className="fs-section fs-benchmark-proofs" aria-labelledby="proofs-title">
          <h2 id="proofs-title">Real failures.</h2>
          <p className="fs-benchmark-proofs-intro">
            Anonymised examples where a small query change—a typo, a synonym,
            a missing space—led to zero results while the control query found
            products.
          </p>
          <div className="fs-proof-cards-grid">
            {data.proof_cards.slice(0, 12).map((card, index) => (
              <ProofCardDisplay key={index} card={card} />
            ))}
          </div>
        </section>
      )}

      {verticals.length > 0 && (
        <section className="fs-section fs-benchmark-verticals" aria-labelledby="verticals-title">
          <h2 id="verticals-title">By vertical.</h2>
          <div className="fs-benchmark-vertical-list">
            {verticals.map(([vertical, stats]) => (
              <div key={vertical} className="fs-benchmark-vertical-row">
                <span className="fs-benchmark-vertical-name">{vertical}</span>
                <span className="fs-benchmark-vertical-count">{stats.count} stores</span>
                <span className="fs-benchmark-vertical-stats">
                  {stats.pass} pass · {stats.fail} fail
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
