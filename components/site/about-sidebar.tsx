import { SpineSidebar } from "@/components/site/spine-sidebar";

const sections = [
  { id: "focus", label: "Focus" },
  { id: "what-we-do", label: "What we do" },
  { id: "background", label: "Expertise" },
  { id: "how-we-audit", label: "Audit method" },
  { id: "what-you-get", label: "Deliverables" },
  { id: "who-we-work-with", label: "Who this is for" },
  { id: "typical-situations", label: "Typical situations" },
  { id: "why-this-studio", label: "Why this studio exists" },
];

export function AboutSidebar() {
  return <SpineSidebar sections={sections} />;
}
