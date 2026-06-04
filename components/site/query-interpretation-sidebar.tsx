import { SpineSidebar } from "@/components/site/spine-sidebar";

const sections = [
  { id: "overview", label: "Overview" },
  { id: "compound-queries", label: "Compound queries" },
  { id: "attribute-queries", label: "Attribute queries" },
  { id: "synonyms-vs-meaning", label: "Synonyms vs meaning" },
  { id: "tokenization", label: "Tokenization" },
  { id: "ambiguous-queries", label: "Ambiguous queries" },
];

export function QueryInterpretationSidebar() {
  return <SpineSidebar sections={sections} />;
}
