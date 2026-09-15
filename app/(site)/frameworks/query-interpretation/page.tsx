import { FrameworkArticle, type FrameworkStage } from "@/components/site/framework-article";
import { JsonLd } from "@/components/seo/json-ld";
import { breadcrumbSchema, createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Query interpretation in ecommerce search | Find Sherpas",
  description:
    "A practical framework for turning ecommerce search queries into product types, attributes, brands, constraints and contextual intent.",
  path: "/frameworks/query-interpretation",
  absoluteTitle: true,
});

const stages: FrameworkStage[] = [
  {
    id: "compound-queries",
    title: "Decompose compound queries",
    summary: "Separate the product the customer wants from the conditions it must satisfy.",
    detail:
      "Compound searches compress several decisions into a few words. The safest interpretation identifies the head product concept first, then attaches attributes, brand, audience, use case and exclusions. Treating every token as equal text often rewards products that match many words while missing the requested product type.",
    example: {
      query: "women’s red waterproof hiking jacket size M",
      weak: "Seven independent keywords competing across titles and descriptions.",
      useful: "Jacket = product; women’s = audience; red, waterproof and M = constraints; hiking = activity context.",
    },
    questions: [
      "What is the head product concept?",
      "Which words narrow eligibility and which only add preference or context?",
      "Can one token belong to more than one field in this catalogue?",
    ],
    evidence: [
      "Parsed tokens, detected entities and generated filters",
      "Result composition when each term is added or removed",
      "Reformulations that simplify a long query into shorter searches",
    ],
    actions: [
      "Define an entity schema that matches the catalogue’s strongest fields",
      "Test compositional queries rather than only single product terms",
      "Keep soft preferences distinct from filters that can cause zero results",
    ],
    decisionRule:
      "Make a term a hard constraint only when its meaning and catalogue coverage are reliable enough to exclude products.",
  },
  {
    id: "attribute-queries",
    title: "Map attributes to catalogue truth",
    summary: "Customer vocabulary and product data must meet in the same field.",
    detail:
      "Shoppers rarely use the exact labels in a product information system. They search for ‘navy’, ‘midnight’ or ‘dark blue’; ‘sofa bed’ or ‘sleeper sofa’. Interpretation should connect those terms to controlled catalogue values without pretending that weak or missing data is precise.",
    example: {
      query: "oak dining table for six",
      weak: "Matches ‘oak effect’ copy and any page mentioning six, including sets of six chairs.",
      useful: "Dining table = product; oak = material requirement; six = seating-capacity intent, verified against structured fields.",
    },
    questions: [
      "Is this value stored consistently and completely for the category?",
      "Is the shopper expressing a strict requirement or a preference?",
      "Do local-language terms map to the same controlled value?",
    ],
    evidence: [
      "Attribute completeness and value distributions by category",
      "Examples of customer terms that lead to the same product family",
      "False positives caused by matching descriptions instead of attributes",
    ],
    actions: [
      "Normalise high-value attribute families and their customer vocabulary",
      "Use category-aware mappings so a term keeps the right meaning",
      "Fall back gracefully when structured data is incomplete",
    ],
    decisionRule:
      "An attribute filter is only as trustworthy as the data behind it. When coverage is weak, prefer a scored signal and expose the limitation.",
  },
  {
    id: "tokenization",
    title: "Normalise without erasing meaning",
    summary: "Small text-processing choices can split brands, sizes and product codes into the wrong pieces.",
    detail:
      "Case folding, punctuation removal, stemming, typo tolerance and token boundaries shape every later match. The right behaviour depends on the catalogue: a hyphen may be noise in one query and essential in a model number; a short token may be a stop word in prose but a clothing size in retail.",
    example: {
      query: "New Balance 530 / EU 39.5",
      weak: "Drops ‘new’, splits the decimal size and fuzzily matches unrelated model numbers.",
      useful: "Preserves the multi-word brand, identifies 530 as a model and normalises 39.5 within the EU size system.",
    },
    questions: [
      "Which punctuation and token boundaries carry meaning in this category?",
      "When should typo tolerance be reduced for brands, SKUs or short queries?",
      "Are stemming and stop-word rules appropriate for every supported language?",
    ],
    evidence: [
      "Raw and analysed token streams for representative queries",
      "False matches around short terms, codes, units and multi-word brands",
      "Zero-result queries differing only by punctuation, accents or inflection",
    ],
    actions: [
      "Create field-specific analysis instead of one analyser for every value",
      "Protect product codes, model names, units and known multi-word brands",
      "Test each language with native examples rather than translated English probes",
    ],
    decisionRule:
      "Normalisation should remove variation, not information. If two forms mean the same thing, converge them; if the distinction changes the product, preserve it.",
  },
  {
    id: "synonyms-vs-meaning",
    title: "Use vocabulary, not synonym sprawl",
    summary: "Equivalence, relatedness and substitution are different relationships.",
    detail:
      "Synonyms are useful when two expressions genuinely denote the same concept in context. They are dangerous when used as a general rescue tool. Related categories, accessories, broader terms and style associations can widen retrieval without being interchangeable—and should be represented differently.",
    example: {
      query: "trainers",
      weak: "A global synonym equates trainers, shoes, running shoes and sneakers in every market and category.",
      useful: "Trainers and sneakers are market-aware vocabulary for a product family; running is an activity refinement, not a universal equivalent.",
    },
    questions: [
      "Are the terms interchangeable in this market and category?",
      "Should expansion work in both directions?",
      "Could the rule introduce accessories, substitutes or broader categories?",
    ],
    evidence: [
      "Results with each expansion enabled separately",
      "Query pairs customers use before and after reformulation",
      "Synonym rules ranked by traffic reach and number of affected categories",
    ],
    actions: [
      "Label vocabulary relationships: equivalent, broader, narrower or related",
      "Scope expansions by category, locale and direction",
      "Retire rules that solve isolated examples but create broad false positives",
    ],
    decisionRule:
      "If substituting term A for term B changes what the shopper could reasonably receive, they are not unconditional synonyms.",
  },
  {
    id: "ambiguous-queries",
    title: "Resolve ambiguity with context",
    summary: "Some queries have more than one valid interpretation; choosing silently is still a product decision.",
    detail:
      "Ambiguity can come from language, catalogue overlap or missing context. Behavioural popularity may provide a prior, but it does not make the minority intent invalid. The interface can preserve useful branches through mixed results, suggestions, categories or clarifying controls instead of forcing one brittle interpretation.",
    example: {
      query: "apple",
      weak: "Assumes the globally popular brand even in a catalogue that also sells groceries.",
      useful: "Uses catalogue and market context, preserves both credible branches and helps the shopper choose when confidence is low.",
    },
    questions: [
      "What are the credible intents in this catalogue and market?",
      "Which signals change the probability: category, session, locale or season?",
      "Can the results page expose both intents without becoming confusing?",
    ],
    evidence: [
      "Click distribution and refinements for the ambiguous query",
      "Previous browsing context, selected category and current market",
      "Abandonment after one interpretation dominates the first page",
    ],
    actions: [
      "Use confidence thresholds rather than forcing a single intent every time",
      "Offer category suggestions or balanced result groups where useful",
      "Review ambiguous high-volume queries as a distinct evaluation class",
    ],
    decisionRule:
      "When confidence is low and the cost of a wrong branch is high, help the shopper disambiguate instead of hiding the uncertainty.",
  },
  {
    id: "interpretation-evaluation",
    title: "Evaluate the interpretation layer",
    summary: "Judge the meaning produced by the system before judging the ranked list.",
    detail:
      "Result relevance alone cannot reveal whether the system understood the query or merely produced an acceptable answer by accident. A durable evaluation records the expected entities and constraints, the system’s interpretation, candidate-set effects and final results separately.",
    example: {
      query: "green dress not silk",
      weak: "Marks the search as successful because several green dresses appear, even though silk products dominate.",
      useful: "Checks product=dress, colour=green and material exclusion=silk before reviewing candidate coverage and order.",
    },
    questions: [
      "What interpretation would a reviewer expect before seeing results?",
      "Which extracted parts should filter, boost, exclude or remain contextual?",
      "Did the right result appear for the right reason?",
    ],
    evidence: [
      "A labelled set of queries with expected entities and relationships",
      "Per-stage traces from raw query to filters and candidates",
      "Error rates by interpretation pattern, language and category",
    ],
    actions: [
      "Score entity detection and relation handling separately from ranking",
      "Add real production failures to a versioned regression set",
      "Review changes across query classes, not only the examples they target",
    ],
    decisionRule:
      "Do not approve an interpretation change because one result page improved. Confirm the intended meaning, the affected candidate set and the regressions it could introduce.",
  },
];

const method = [
  {
    title: "Create a query grammar",
    description:
      "List the concepts customers combine in your catalogue: product types, brands, attributes, audiences, use cases, quantities, units and exclusions. Add market-specific language.",
    output: "A practical taxonomy of query parts grounded in the catalogue.",
  },
  {
    title: "Label real and deliberate queries",
    description:
      "Sample production searches, then add probes that exercise composition, ambiguity, typos, punctuation and local inflection. Label expected entities before looking at the result page.",
    output: "A balanced interpretation set instead of a list of favourite examples.",
  },
  {
    title: "Trace meaning into retrieval",
    description:
      "Compare expected and observed tokens, entities, filters, expansions and exclusions. Then inspect how each choice changes candidate coverage.",
    output: "An error map connecting language failures to catalogue consequences.",
  },
  {
    title: "Choose the least brittle intervention",
    description:
      "Prefer improvements that generalise across a query class: cleaner attributes, scoped vocabulary, better analysis or explicit parsing. Treat one-off rules as temporary and owned.",
    output: "A prioritised backlog with a test, owner and rollback path for each change.",
  },
];

const worksheetRows = [
  { field: "Raw query", capture: "Exact text, language, market and any session context", reason: "Interpretation begins with what the system actually received." },
  { field: "Expected structure", capture: "Product, brand, attributes, constraints, context and relationships", reason: "Separates human expectation from the current implementation." },
  { field: "Observed structure", capture: "Tokens, entities, expansions, filters, exclusions and confidence", reason: "Shows precisely where meaning changed." },
  { field: "Candidate effect", capture: "Products added, removed or unexpectedly retained", reason: "Connects a language decision to a shopper-visible consequence." },
  { field: "Intervention", capture: "Data, analyser, vocabulary, parser, UI or ranking change", reason: "Points the fix at the layer that created the error." },
];

export default function QueryInterpretationPage() {
  return (
    <>
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Resources", path: "/resources" },
          { name: "Query interpretation", path: "/frameworks/query-interpretation" },
        ])}
      />
      <FrameworkArticle
        title="Turn customer language into searchable meaning."
        introduction="Ranking can only order the candidates it receives. This framework shows how to decompose ecommerce queries, connect them to catalogue data and preserve uncertainty when more than one interpretation is credible."
        principle="Interpret first, retrieve second, rank third. A perfectly ordered list of products for the wrong meaning is still a failed search."
        scope="Use it with lexical, semantic or hybrid search. The concepts stay the same even when the implementation changes."
        flow={["Raw query", "Normalise", "Identify", "Relate", "Retrieve", "Verify"]}
        stages={stages}
        methodTitle="Build interpretation as an observable layer."
        methodIntroduction="The aim is not an ever-growing rule list. It is a small, explicit model of customer language that can be tested against catalogue truth and improved without hiding regressions."
        method={method}
        worksheetRows={worksheetRows}
        related={{
          href: "/frameworks/search-failure-modes",
          title: "Search failure modes",
          description: "Place interpretation inside the wider search system diagnosis.",
        }}
      />
    </>
  );
}
