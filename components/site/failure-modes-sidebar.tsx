import { SpineSidebar } from "@/components/site/spine-sidebar";

const sections = [
  { id: "overview", label: "Overview" },
  { id: "query-understanding", label: "Query understanding" },
  { id: "ranking", label: "Ranking failures" },
  { id: "coverage", label: "Coverage failures" },
  { id: "evaluation", label: "Evaluation failures" },
  { id: "merchandising", label: "Merchandising distortions" },
  { id: "operational-drift", label: "Operational drift" },
];

export function FailureModesSidebar() {
  return <SpineSidebar sections={sections} />;
}
