"use client";

import { useState, useSyncExternalStore } from "react";
import { Play } from "lucide-react";

const mobileQuery = "(max-width: 760px)";
function subscribeToViewport(onChange: () => void) {
  const query = window.matchMedia(mobileQuery);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}
const getMobileSnapshot = () => window.matchMedia(mobileQuery).matches;
const getServerSnapshot = () => false;

const examples = [
  {
    title: "An occasion",
    query: "black dress for winter wedding",
    video: "search-loop",
    poster: "poster",
    explanation:
      "The words match, but the occasion is lost. Relevance needs to account for the kind of dress the customer is looking for.",
  },
  {
    title: "A typo",
    query: "wirless headphones",
    video: "search-loop-typo",
    poster: "poster-typo",
    explanation:
      "A missing letter should not turn headphones into cables. Check how typo handling interacts with product relevance.",
  },
  {
    title: "A local expression",
    query: "trainers for running",
    video: "search-loop-synonym",
    poster: "poster-synonym",
    explanation:
      "Your customers may use different names for the same product. Synonyms need the context of the category and market.",
  },
  {
    title: "A product type",
    query: "linen shirt",
    video: "search-loop-availability",
    poster: "poster-availability",
    explanation:
      "Matching a material is not enough. A query for a linen shirt should not be led by bed linen.",
  },
  {
    title: "Mixed relevance",
    query: "black occasion dress",
    video: "search-loop-purity",
    poster: "poster-purity",
    explanation:
      "Finding one strong result is not enough when the rest of the top set is noisy. We look at the quality of the whole result set.",
  },
  {
    title: "An exclusion",
    query: "wireless headphones not earbuds",
    video: "search-loop-negative",
    poster: "poster-negative",
    explanation:
      "The category is right, but the exclusion is ignored. Negative intent needs to be evaluated separately from topical relevance.",
  },
  {
    title: "Variant flooding",
    query: "running shoes",
    video: "search-loop-variants",
    poster: "poster-variants",
    explanation:
      "Six colourways of one model can look relevant while offering very little choice. Broad queries need useful variety as well as matching products.",
  },
];

export function SearchDemonstration() {
  const [selected, setSelected] = useState(0);
  const [playing, setPlaying] = useState(false);
  const mobile = useSyncExternalStore(
    subscribeToViewport,
    getMobileSnapshot,
    getServerSnapshot,
  );
  const suffix = mobile ? "-mobile" : "";
  const example = examples[selected];
  return (
    <div className="fs-shop-demo">
      <div className="fs-demo-tabs" role="group" aria-label="Search scenario">
        {examples.map((item, index) => (
          <button
            key={item.title}
            type="button"
            aria-pressed={selected === index}
            onClick={() => {
              setSelected(index);
              setPlaying(false);
            }}
          >
            {item.title}
          </button>
        ))}
      </div>
      <div className="fs-demo-media">
        {!playing ? (
          <button
            type="button"
            className="fs-demo-preview"
            onClick={() => setPlaying(true)}
            aria-label={`Play example: ${example.title}`}
          >
            <picture>
              <source
                media={mobileQuery}
                srcSet={`/video/${example.poster}-mobile.jpg`}
              />
              {/* These local poster variants preserve the original demo framing. */}
              <img src={`/video/${example.poster}.jpg`} alt="" loading="lazy" />
            </picture>
            <span className="fs-demo-play-label">
              <Play size={20} fill="currentColor" aria-hidden="true" />
              Play example
            </span>
          </button>
        ) : (
          <video
            key={example.video + suffix}
            controls
            autoPlay
            muted
            playsInline
            preload="metadata"
            poster={`/video/${example.poster}${suffix}.jpg`}
            aria-label={`Illustration: ${example.query}. ${example.explanation}`}
            aria-describedby="demo-explanation"
          >
            <source
              src={`/video/${example.video}${suffix}.mp4`}
              type="video/mp4"
            />
            Your browser cannot play this video.
          </video>
        )}
      </div>
      <div
        className="fs-demo-description"
        id="demo-explanation"
        aria-live="polite"
      >
        <p>
          <strong>{example.query}</strong>
        </p>
        <p>{example.explanation}</p>
      </div>
      <p className="fs-demo-caption">
        NORTHAM is a fictional retailer. The video is an illustration, not a
        client result. Press play to see the change.
      </p>
    </div>
  );
}
