import { FrameworkArticle, type FrameworkStage } from "@/components/site/framework-article";
import { JsonLd } from "@/components/seo/json-ld";
import { breadcrumbSchema, createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Search failure modes | Find Sherpas",
  description:
    "A practical framework for diagnosing ecommerce search failures across interpretation, coverage, ranking, evaluation, merchandising and operations.",
  path: "/frameworks/search-failure-modes",
  absoluteTitle: true,
});

const stages: FrameworkStage[] = [
  {
    id: "query-understanding",
    title: "Query understanding",
    summary: "The system builds the wrong meaning before retrieval begins.",
    detail:
      "A query is not merely a string. It can contain a product type, attributes, a brand, a use case and constraints. When those parts are flattened or mapped to the wrong fields, the engine retrieves a plausible but fundamentally wrong candidate set.",
    example: {
      query: "black waterproof hiking jacket",
      weak: "Matches any product containing several of the words, including black hiking trousers and water-resistant casual jackets.",
      useful: "Treats jacket as the product type; black and waterproof as constraints; hiking as activity context.",
    },
    questions: [
      "Which parts of the query describe the product, and which constrain it?",
      "Are customer terms mapped to the catalogue language used in this market?",
      "Does the interpretation change when word order, spelling or language changes?",
    ],
    evidence: [
      "Parsed-query output, applied filters and rewritten terms",
      "Searches reformulated immediately after the first results page",
      "Results grouped by query class: product, attribute, brand and use case",
    ],
    actions: [
      "Create a labelled query set before changing synonyms or boosts",
      "Map high-value concepts to explicit attributes where the data supports it",
      "Test the same intent across spelling, inflection and local vocabulary",
    ],
    decisionRule:
      "If the right products never enter the candidate set because the query was misread, fix interpretation before ranking.",
  },
  {
    id: "ranking",
    title: "Ranking",
    summary: "Relevant products are present, but the order does not reflect the shopper’s intent.",
    detail:
      "Ranking decides which eligible products earn attention. Problems appear when broad text matches outweigh exact product-type matches, business signals dominate relevance, or one global formula is expected to serve every query class equally well.",
    example: {
      query: "linen shirt",
      weak: "A linen-blend scarf and a cotton shirt with ‘linen look’ copy outrank an in-stock linen shirt.",
      useful: "Exact product type and material matches lead, with availability and business signals used as controlled tie-breakers.",
    },
    questions: [
      "Is the first result defensible for this query, not merely relevant somewhere?",
      "Which signals determine the top positions for exact, broad and category queries?",
      "Do out-of-stock, low-quality or duplicate products crowd out stronger options?",
    ],
    evidence: [
      "Top 10 results with matched fields and score contributions",
      "Clicks, add-to-basket events and reformulations by query class",
      "Before-and-after judgements from a fixed relevance set",
    ],
    actions: [
      "Separate exact product and attribute matches from loose description matches",
      "Tune by query class rather than relying on one universal weighting",
      "Introduce business signals gradually and test their relevance cost",
    ],
    decisionRule:
      "If good candidates exist but sit below weaker ones, the problem is ranking. If they are absent, return to interpretation or coverage.",
  },
  {
    id: "coverage",
    title: "Coverage and retrieval",
    summary: "Products that should qualify never become candidates.",
    detail:
      "Coverage is the boundary between the catalogue and the searchable index. Missing attributes, stale feeds, aggressive filters, field configuration and locale-specific gaps can all make a product invisible even though it exists and is available to buy.",
    example: {
      query: "size 38 trail shoes",
      weak: "Returns zero results because sizes are stored as variant strings that the search index does not expose.",
      useful: "Retrieves trail shoes with an available size-38 variant, then ranks them using product and activity relevance.",
    },
    questions: [
      "Does the product exist, is it indexed, and is it eligible in this market?",
      "Which filter or field removed it from the candidate set?",
      "Are product and variant availability represented consistently?",
    ],
    evidence: [
      "Catalogue-to-index record counts and freshness timestamps",
      "Field completeness by category, market and variant",
      "Zero- and low-result queries replayed with filters removed one at a time",
    ],
    actions: [
      "Trace representative SKUs from source catalogue to final index",
      "Measure attribute completeness before building rules around an attribute",
      "Add monitoring for feed failures, stale records and unexpected count shifts",
    ],
    decisionRule:
      "Do not compensate for missing candidates with ranking weights. Prove that eligible products are indexed and retrievable first.",
  },
  {
    id: "evaluation",
    title: "Evaluation",
    summary: "The team cannot tell whether a change improved search or moved the failure elsewhere.",
    detail:
      "Search quality can look better in hand-picked examples while worsening across long-tail, multilingual or high-volume query groups. Evaluation fails when teams lack a stable query set, explicit judgements, segmented behavioural measures and safeguards for commercial side effects.",
    example: {
      query: "A synonym change fixes ten visible searches",
      weak: "The change ships because the demo looks better, without checking false matches or other markets.",
      useful: "The same change is replayed against labelled query groups, inspected for regressions, then measured in real use where traffic permits.",
    },
    questions: [
      "What specific behaviour should improve, for which query group?",
      "Which known-good searches must not regress?",
      "Can the event tracking distinguish a useful result from a desperate click?",
    ],
    evidence: [
      "A versioned judgement set with query intent and expected products",
      "Behavioural metrics segmented by query class, device and market",
      "Change logs connecting configuration releases to metric movement",
    ],
    actions: [
      "Define the hypothesis and guardrails before changing configuration",
      "Combine offline relevance review with behavioural evidence",
      "Keep a regression set built from real failures and important queries",
    ],
    decisionRule:
      "A change is not an improvement until the team can name who it helps, how that will be observed and what must remain stable.",
  },
  {
    id: "merchandising",
    title: "Merchandising distortion",
    summary: "Commercial rules override the intent that brought the shopper to search.",
    detail:
      "Boosts, pinned products, campaigns and stock priorities are legitimate inputs. They become harmful when they are opaque, permanent or broad enough to outrank clearly better matches. The goal is not relevance without commerce; it is commercial influence with explicit limits.",
    example: {
      query: "blue wool coat",
      weak: "A campaign pins discounted polyester jackets above exact wool coats for every coat-related query.",
      useful: "Exact blue wool coats remain the core result set; eligible campaign products receive a bounded boost within that set.",
    },
    questions: [
      "Would this product rank highly without the commercial rule?",
      "What query scope, market and dates should limit the rule?",
      "Who owns expiry and review when the campaign ends?",
    ],
    evidence: [
      "Active rules with owners, scopes, start dates and expiry dates",
      "Rank positions with commercial boosts switched on and off",
      "Engagement and reformulation for queries touched by each rule",
    ],
    actions: [
      "Apply boosts only after basic eligibility and relevance are satisfied",
      "Give every temporary rule an owner and automatic expiry",
      "Audit rules by reach so the broadest interventions are reviewed first",
    ],
    decisionRule:
      "A business rule may choose among relevant options; it should not redefine what the query means.",
  },
  {
    id: "operational-drift",
    title: "Operational drift",
    summary: "Individually reasonable changes accumulate into an unowned system.",
    detail:
      "Search is a living product. Catalogue changes, platform upgrades, new markets, undocumented rules and one-off fixes gradually separate the current behaviour from the original design. Drift is usually slow enough to escape incident processes and broad enough to resist one tuning session.",
    example: {
      query: "The same search, six months later",
      weak: "New attributes are not indexed, old synonyms remain active and overlapping rules produce an unexplained order.",
      useful: "Configuration, data health and relevance sets are reviewed on a cadence, with ownership and rollback information.",
    },
    questions: [
      "Who can explain the current configuration and approve a change?",
      "Which rules, synonyms or fields no longer match the catalogue?",
      "What changed in search behaviour after the last platform or feed release?",
    ],
    evidence: [
      "Configuration history, release notes and rule ownership",
      "Trend lines for coverage, zero results and repeated reformulation",
      "Scheduled replays of the relevance and data-quality sets",
    ],
    actions: [
      "Treat search configuration as versioned product logic",
      "Assign ownership for data, relevance, merchandising and measurement",
      "Review the highest-reach rules and weakest query groups regularly",
    ],
    decisionRule:
      "When failures span several stages and nobody can trace why, restore observability and ownership before adding more fixes.",
  },
];

const method = [
  {
    title: "Build a representative query set",
    description:
      "Sample high-volume, high-value, zero-result and reformulated searches. Add deliberate probes for products, attributes, brands, use cases, ambiguity and local language.",
    output: "A query set labelled by intent, market and business importance.",
  },
  {
    title: "Replay and classify the failure",
    description:
      "For each query, inspect the interpretation, candidate set, order and applied rules. Assign the earliest stage where behaviour diverges from the expected result.",
    output: "A failure map that separates root causes from visible symptoms.",
  },
  {
    title: "Prioritise patterns, not anecdotes",
    description:
      "Group failures by cause and estimate reach using query frequency, affected catalogue areas, market importance and severity for the shopper.",
    output: "A short backlog ordered by customer reach, confidence and effort.",
  },
  {
    title: "Change one layer and measure",
    description:
      "State the hypothesis, expected query groups and guardrails. Replay the fixed set before release and use real behavioural testing when volume and instrumentation allow.",
    output: "A decision to keep, adjust or reverse—with the evidence attached.",
  },
];

const worksheetRows = [
  { field: "Query and market", capture: "Raw query, language, device and market", reason: "Meaning and expected results vary by context." },
  { field: "Expected intent", capture: "Product type, attributes, brand, use case and constraints", reason: "Makes the relevance judgement explicit." },
  { field: "Observed behaviour", capture: "Interpretation, candidate count, top results and applied rules", reason: "Locates the earliest stage that failed." },
  { field: "Failure class", capture: "Interpretation, ranking, coverage, evaluation, merchandising or drift", reason: "Prevents a visible symptom becoming the diagnosis." },
  { field: "Evidence and action", capture: "Supporting data, proposed change, measure and guardrail", reason: "Turns the finding into a testable improvement." },
];

export default function SearchFailureModesPage() {
  return (
    <>
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Resources", path: "/resources" },
          { name: "Search failure modes", path: "/frameworks/search-failure-modes" },
        ])}
      />
      <FrameworkArticle
        title="Find where search actually breaks."
        introduction="A poor result page is the end of a chain, not the diagnosis. This framework helps ecommerce teams locate the earliest failure, gather the right evidence and choose a fix that addresses the cause."
        principle="Fix the earliest broken stage. Every downstream layer inherits what the stage before it misunderstood, excluded or distorted."
        scope="Vendor-agnostic. Designed for catalogue search across markets, languages and search platforms."
        flow={["Interpret", "Retrieve", "Rank", "Evaluate", "Merchandise", "Maintain"]}
        stages={stages}
        methodTitle="Turn the framework into a working review."
        methodIntroduction="The useful unit is not a single bad screenshot. It is a repeated failure pattern connected to evidence, an owner and a measurable next action."
        method={method}
        worksheetRows={worksheetRows}
        related={{
          href: "/frameworks/query-interpretation",
          title: "Query interpretation",
          description: "Go deeper on how raw customer language becomes searchable meaning.",
        }}
      />
    </>
  );
}
