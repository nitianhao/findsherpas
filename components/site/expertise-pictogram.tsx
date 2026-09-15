import Image from "next/image";

type ExpertiseIllustrationProps = {
  kind:
    | "analytics"
    | "relevance"
    | "experience"
    | "experimentation"
    | "development";
};

const illustrations = {
  analytics: {
    src: "/images/expertise/search-analytics-collage.png",
    alt: "Search signals becoming a clear analytics trend",
  },
  relevance: {
    src: "/images/expertise/query-relevance-collage.png",
    alt: "A search lens bringing the most relevant product forward",
  },
  experience: {
    src: "/images/expertise/search-ux-collage.png",
    alt: "A smooth path from search through filters to a product result",
  },
  experimentation: {
    src: "/images/expertise/experimentation-collage.png",
    alt: "Two experimental paths resolving into a winning result",
  },
  development: {
    src: "/images/expertise/semantic-search-collage.png",
    alt: "A semantic search core connecting related products and data",
  },
} satisfies Record<
  ExpertiseIllustrationProps["kind"],
  { src: string; alt: string }
>;

export function ExpertiseIllustration({ kind }: ExpertiseIllustrationProps) {
  const illustration = illustrations[kind];

  return (
    <div className="fs-expertise-illustration">
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
