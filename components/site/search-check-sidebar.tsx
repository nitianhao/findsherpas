import { SpineSidebar } from "@/components/site/spine-sidebar";

const sections = [
  { id: "overview", label: "Overview" },
  { id: "assessment", label: "The checks" },
  { id: "interpretation", label: "Interpreting results" },
  { id: "contact", label: "Get help" },
];

export function SearchCheckSidebar() {
  return <SpineSidebar sections={sections} />;
}
