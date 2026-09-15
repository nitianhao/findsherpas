"use client";

import { ArrowRight } from "lucide-react";
import { useMemo, useState } from "react";

type Rating = "good" | "weak" | "miss";

type Probe = {
  id: string;
  title: string;
  instruction: string;
  comparison: [string, string];
  good: string;
  warning: string;
};

const probes: Probe[] = [
  {
    id: "known-item",
    title: "Can search find an exact product?",
    instruction:
      "Copy the full name of an in-stock product and search it exactly as written. This is your retrieval baseline.",
    comparison: ["Known product title", "Exact-title search"],
    good: "The product is first, or immediately visible when genuine variants share the name.",
    warning:
      "No result, a buried exact match, or unrelated products above it can point to missing searchable data, indexing gaps or an override.",
  },
  {
    id: "typo",
    title: "Does one small typo become a dead end?",
    instruction:
      "Take a common product query that works and transpose or replace one letter. Compare the two result sets.",
    comparison: ["running shoes", "runnign shoes"],
    good: "The intended category still appears, or one clear correction gets the shopper there.",
    warning:
      "Zero results or a different product type suggests weak typo tolerance or normalization.",
  },
  {
    id: "vocabulary",
    title: "Does search understand customer vocabulary?",
    instruction:
      "Compare your catalogue term with a common synonym or regional expression your customers actually use.",
    comparison: ["sneakers", "trainers"],
    good: "Both phrases reach the same intended category without unrelated products taking over.",
    warning:
      "A large change can expose a vocabulary gap. Check the meaning, not just whether a synonym rule fired.",
  },
  {
    id: "constraint",
    title: "Is one explicit constraint respected?",
    instruction:
      "Add exactly one visible, verifiable requirement to a working product query—colour, material, audience, size or availability.",
    comparison: ["hiking boots", "waterproof hiking boots"],
    good: "The first results satisfy the added requirement and still match the product type.",
    warning:
      "If the base product matches but the requirement disappears, search is retrieving words without preserving intent.",
  },
  {
    id: "language",
    title: "Does local language survive normalization?",
    instruction:
      "Try one realistic local variation: missing diacritics, plural form, or a word shoppers commonly merge or split.",
    comparison: ["löparskor", "loparskor"],
    good: "The same product category remains visible with a similarly useful range of results.",
    warning:
      "A few coincidental matches are not recovery. A thin or off-topic result set still indicates a language-handling gap.",
  },
  {
    id: "narrowing",
    title: "Can a mobile shopper narrow the results?",
    instruction:
      "On a phone-sized screen, run a broad product search and apply one useful filter such as size, price or in-stock status.",
    comparison: ["Broad result set", "One useful filter"],
    good: "Filters are easy to find, use plain language and never offer a selectable option that leads nowhere.",
    warning:
      "A hidden filter control, confusing values or a zero-result combination makes refinement feel unreliable.",
  },
];

const ratings: { value: Rating; label: string }[] = [
  { value: "good", label: "Looks good" },
  { value: "weak", label: "Usable, but weak" },
  { value: "miss", label: "Clear miss" },
];

export function SearchCheckAssessment() {
  const [answers, setAnswers] = useState<Partial<Record<string, Rating>>>({});

  const summary = useMemo(() => {
    const values = Object.values(answers);
    return {
      reviewed: values.length,
      good: values.filter((value) => value === "good").length,
      weak: values.filter((value) => value === "weak").length,
      miss: values.filter((value) => value === "miss").length,
    };
  }, [answers]);

  const complete = summary.reviewed === probes.length;
  const outcome = !complete
    ? {
        title: "Complete all six probes to see the pattern.",
        text: "Judge the visible customer experience, not whether the engine technically returned something.",
      }
    : summary.miss > 0
      ? {
          title: "You found a customer-visible search failure.",
          text: `${summary.miss} clear ${summary.miss === 1 ? "miss" : "misses"} and ${summary.weak} weaker ${summary.weak === 1 ? "result" : "results"}. Prioritise dead ends, wrong product types and ignored constraints before minor ranking changes.`,
        }
      : summary.weak >= 2
        ? {
            title: "There is a pattern worth diagnosing.",
            text: `${summary.weak} probes added noticeable friction. Search may be returning plausible products while still making customers work too hard.`,
          }
        : {
            title: "No obvious high-risk failure surfaced.",
            text: "That is a good signal, not a clean bill of health. Six hand-picked probes cannot measure coverage across your full query log, catalogue or markets.",
          };

  return (
    <section className="fs-section fs-check-assessment" aria-labelledby="check-probes-title">
      <div className="fs-check-assessment-heading">
        <h2 id="check-probes-title">Six probes. Change one thing at a time.</h2>
        <p>
          Mark what you see after each test. “Usable, but weak” means a shopper
          can recover; “clear miss” means the experience gives them a credible
          reason to leave.
        </p>
      </div>

      <div className="fs-check-probes">
        {probes.map((probe, index) => (
          <article className="fs-check-probe" key={probe.id}>
            <p className="fs-check-number">
              {index + 1} / {probes.length}
            </p>
            <div className="fs-check-probe-body">
              <h3>{probe.title}</h3>
              <p>{probe.instruction}</p>
              <div
                className="fs-check-comparison"
                aria-label={`${probe.comparison[0]} compared with ${probe.comparison[1]}`}
              >
                <span>{probe.comparison[0]}</span>
                <ArrowRight size={19} aria-hidden="true" />
                <span>{probe.comparison[1]}</span>
              </div>
              <dl className="fs-check-signals">
                <div>
                  <dt>Good signal</dt>
                  <dd>{probe.good}</dd>
                </div>
                <div>
                  <dt>Warning signal</dt>
                  <dd>{probe.warning}</dd>
                </div>
              </dl>
              <div
                className="fs-check-rating"
                role="group"
                aria-label={`Result for ${probe.title}`}
              >
                {ratings.map((rating) => (
                  <button
                    key={rating.value}
                    type="button"
                    className={`fs-check-rating-${rating.value}`}
                    aria-pressed={answers[probe.id] === rating.value}
                    onClick={() =>
                      setAnswers((current) => ({
                        ...current,
                        [probe.id]: rating.value,
                      }))
                    }
                  >
                    {rating.label}
                  </button>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="fs-check-result" id="interpretation">
        <div className="fs-check-progress">
          <p>
            {summary.reviewed} of {probes.length} probes reviewed
          </p>
          <div aria-hidden="true">
            <span
              style={{ transform: `scaleX(${summary.reviewed / probes.length})` }}
            />
          </div>
        </div>
        <div className="fs-check-counts" aria-label="Assessment totals">
          <div>
            <strong>{summary.good}</strong>
            <span>Looks good</span>
          </div>
          <div>
            <strong>{summary.weak}</strong>
            <span>Usable, but weak</span>
          </div>
          <div>
            <strong>{summary.miss}</strong>
            <span>Clear miss</span>
          </div>
        </div>
        <div className="fs-check-outcome" role="status" aria-live="polite">
          <h3>{outcome.title}</h3>
          <p>{outcome.text}</p>
        </div>
        {summary.reviewed > 0 && (
          <div className="fs-check-result-actions">
            <button
              type="button"
              className="fs-check-reset"
              onClick={() => setAnswers({})}
            >
              Reset the check
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
