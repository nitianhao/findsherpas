"use client";

import { useEffect, useState } from "react";

const rotationInterval = 3600;

const queries = [
  {
    language: "English",
    lang: "en",
    first: "navy",
    second: "trainers",
    bridge: "for",
    context: "fell running",
    firstLabel: "Colour",
    secondLabel: "Product",
    contextStart: "Activity",
    contextEnd: "Terrain",
    note: "In British English, “trainers” and “fell running” describe a specific product and use case. A search tuned only for sneakers or generic running can miss both.",
  },
  {
    language: "Deutsch",
    lang: "de",
    first: "wasserdichte",
    second: "Wanderschuhe",
    bridge: "für",
    context: "Damen",
    firstLabel: "Feature",
    secondLabel: "Product",
    contextStart: "Audience",
    contextEnd: "Fit",
    note: "German combines concepts inside words and changes their endings. Search needs to connect “Wanderschuhe” with hiking footwear while retaining the waterproof and women’s-fit requirements.",
  },
  {
    language: "Français",
    lang: "fr",
    first: "robe",
    second: "mi-longue",
    bridge: "pour un",
    context: "mariage civil",
    firstLabel: "Product",
    secondLabel: "Length",
    contextStart: "Occasion",
    contextEnd: "Formality",
    note: "French shoppers often express product attributes as part of a phrase. “Mi-longue” is a length, while “mariage civil” implies a different level of formality from a generic wedding search.",
  },
  {
    language: "Nederlands",
    lang: "nl",
    first: "regenjas",
    second: "dames",
    bridge: "voor op de",
    context: "fiets",
    firstLabel: "Product",
    secondLabel: "Audience",
    contextStart: "Use",
    contextEnd: "Context",
    note: "“Voor op de fiets” is a natural Dutch way to describe intended use, not a catalogue phrase. Search has to understand the expression and the compound “regenjas,” not just match isolated words.",
  },
  {
    language: "Español",
    lang: "es",
    first: "zapatillas",
    second: "ligeras",
    bridge: "para",
    context: "correr por montaña",
    firstLabel: "Product",
    secondLabel: "Feature",
    contextStart: "Activity",
    contextEnd: "Terrain",
    note: "Product vocabulary varies across Spanish-speaking markets, and adjective agreement carries attribute information. The full phrase means lightweight trail-running shoes—not simply any light shoe.",
  },
  {
    language: "Svenska",
    lang: "sv",
    first: "fodrade",
    second: "löparskor",
    bridge: "för",
    context: "vinterväglag",
    firstLabel: "Feature",
    secondLabel: "Product",
    contextStart: "Season",
    contextEnd: "Conditions",
    note: "Swedish compounds pack the product and its use into single words. “Löparskor” and “vinterväglag” need careful decomposition so winter road conditions remain part of the intent.",
  },
  {
    language: "Dansk",
    lang: "da",
    first: "løbesko",
    second: "med støtte",
    bridge: "til",
    context: "brede fødder",
    firstLabel: "Product",
    secondLabel: "Feature",
    contextStart: "Fit",
    contextEnd: "Anatomy",
    note: "Danish shoppers can describe fit as a natural phrase rather than a filter value. Search should connect “brede fødder” to width and fit attributes without losing the support requirement.",
  },
] as const;

export function QueryInterpretation() {
  const [selected, setSelected] = useState(0);
  const [automatic, setAutomatic] = useState(true);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(true);
  const query = queries[selected];

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setPrefersReducedMotion(mediaQuery.matches);

    updatePreference();
    mediaQuery.addEventListener("change", updatePreference);
    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    if (!automatic || prefersReducedMotion) return;

    const interval = window.setInterval(() => {
      setSelected((current) => (current + 1) % queries.length);
    }, rotationInterval);

    return () => window.clearInterval(interval);
  }, [automatic, prefersReducedMotion]);

  const stopAutomaticRotation = () => setAutomatic(false);

  return (
    <div className="fs-query-panel">
      <div className="fs-query-words" lang={query.lang} key={query.lang}>
        <div className="fs-query-row">
          <span>{query.first}</span>
          <span className="fs-annotation" lang="en">
            {query.firstLabel}
          </span>
        </div>
        <div className="fs-query-row">
          <span>{query.second}</span>
          <span className="fs-annotation" lang="en">
            {query.secondLabel}
          </span>
        </div>
        <div className="fs-query-bridge">{query.bridge}</div>
        <div className="fs-query-context">
          <mark>{query.context}</mark>
          <div className="fs-context-labels" lang="en">
            <span>{query.contextStart}</span>
            <span>{query.contextEnd}</span>
          </div>
        </div>
      </div>
      <div className="fs-query-bottom">
        <div
          className="fs-language-switch"
          role="group"
          aria-label="Example language"
          onFocusCapture={stopAutomaticRotation}
        >
          {queries.map((item, index) => (
            <button
              key={item.lang}
              type="button"
              aria-pressed={selected === index}
              onClick={() => {
                stopAutomaticRotation();
                setSelected(index);
              }}
              lang={item.lang}
            >
              {item.language}
            </button>
          ))}
        </div>
        <p className="fs-query-note" aria-live={automatic ? "off" : "polite"}>
          {query.note}
        </p>
        <p className="fs-query-caption">
          Illustrative query analysis. Languages rotate automatically; select
          one to pause and explore.
        </p>
      </div>
    </div>
  );
}
