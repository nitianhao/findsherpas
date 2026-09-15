import Image from "next/image";

type ApproachIllustrationProps = {
  kind: "read" | "prioritize" | "handoff" | "measure";
};

const illustrations = {
  read: {
    src: "/images/approach/read-the-search.png",
    alt: "A customer search journey traced to the point where it breaks",
  },
  prioritize: {
    src: "/images/approach/prioritize-changes.png",
    alt: "Search findings sorted by impact and effort",
  },
  handoff: {
    src: "/images/approach/engineering-handoff.png",
    alt: "Search evidence consolidated into an implementation-ready specification",
  },
  measure: {
    src: "/images/approach/measure-and-iterate.png",
    alt: "A changed search result checked against its baseline and refined",
  },
} satisfies Record<
  ApproachIllustrationProps["kind"],
  { src: string; alt: string }
>;

export function ApproachIllustration({ kind }: ApproachIllustrationProps) {
  const illustration = illustrations[kind];

  return (
    <div className="fs-approach-illustration">
      <Image
        src={illustration.src}
        alt={illustration.alt}
        width={960}
        height={656}
        sizes="(max-width: 720px) 180px, (max-width: 1100px) 230px, 290px"
      />
    </div>
  );
}
