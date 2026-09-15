"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { ArrowUp } from "lucide-react";

export function BackToTop() {
  const [isVisible, setIsVisible] = useState(false);
  const [bottomOffset, setBottomOffset] = useState(28);

  useEffect(() => {
    const updateVisibility = () => {
      setIsVisible(window.scrollY > Math.max(window.innerHeight * 0.75, 520));
    };

    const updatePlacement = () => {
      const baseOffset = window.innerWidth <= 760 ? 16 : 28;
      const consent = document.querySelector<HTMLElement>(".fs-consent");
      const consentOffset = consent
        ? window.innerHeight - consent.getBoundingClientRect().top + 12
        : 0;

      setBottomOffset(Math.max(baseOffset, consentOffset));
    };

    const mutationObserver = new MutationObserver(updatePlacement);
    const resizeObserver = new ResizeObserver(updatePlacement);
    const consent = document.querySelector<HTMLElement>(".fs-consent");

    mutationObserver.observe(document.body, { childList: true, subtree: true });
    if (consent) resizeObserver.observe(consent);

    updateVisibility();
    updatePlacement();
    window.addEventListener("scroll", updateVisibility, { passive: true });
    window.addEventListener("resize", updatePlacement);
    return () => {
      window.removeEventListener("scroll", updateVisibility);
      window.removeEventListener("resize", updatePlacement);
      mutationObserver.disconnect();
      resizeObserver.disconnect();
    };
  }, []);

  const scrollToTop = () => {
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  };

  return (
    <button
      type="button"
      className={`fs-back-to-top${isVisible ? " fs-back-to-top-visible" : ""}`}
      style={{ "--fs-back-to-top-bottom": `${bottomOffset}px` } as CSSProperties}
      onClick={scrollToTop}
      aria-label="Scroll to the top of the page"
      aria-hidden={!isVisible}
      tabIndex={isVisible ? 0 : -1}
    >
      To the top
      <ArrowUp size={18} aria-hidden="true" />
    </button>
  );
}
