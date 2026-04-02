import { SpineSidebar } from "@/components/site/spine-sidebar";

const sections = [
  { id: "hero", label: "Overview" },
  { id: "search-problem", label: "The problem" },
  { id: "what-we-do", label: "What we find" },
  { id: "how-we-diagnose", label: "Methodology" },
  { id: "frameworks", label: "Frameworks" },
  { id: "expertise", label: "Expertise" },
  { id: "diagnostic-output", label: "Deliverables" },
  { id: "homepage-cta", label: "Get in touch" },
];

export function HomeSidebar() {
  return <SpineSidebar sections={sections} />;
}
