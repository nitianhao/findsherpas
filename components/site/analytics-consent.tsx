"use client";

import Link from "next/link";
import Script from "next/script";
import { useSyncExternalStore } from "react";

const STORAGE_KEY = "find-sherpas:analytics-consent";
const ANALYTICS_ID = "G-M8D3D607D7";

type Consent = "accepted" | "declined" | null | undefined;

const CONSENT_EVENT = "find-sherpas:analytics-consent-change";
let volatileConsent: Consent = undefined;

function readConsent(): Consent {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved === "accepted" || saved === "declined"
      ? saved
      : (volatileConsent ?? null);
  } catch {
    return volatileConsent ?? null;
  }
}

function subscribe(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(CONSENT_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(CONSENT_EVENT, onStoreChange);
  };
}

export function AnalyticsConsent() {
  const consent = useSyncExternalStore(subscribe, readConsent, () => undefined);

  const choose = (value: Exclude<Consent, null | undefined>) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // The current-page choice still applies when browser storage is unavailable.
    }
    volatileConsent = value;
    if (value === "declined") {
      const analyticsWindow = window as Window & {
        gtag?: (...args: unknown[]) => void;
      };
      analyticsWindow.gtag?.("consent", "update", {
        analytics_storage: "denied",
      });
    }
    window.dispatchEvent(new Event(CONSENT_EVENT));
  };

  return (
    <>
      {consent === "accepted" && (
        <>
          <Script
            strategy="afterInteractive"
            src={`https://www.googletagmanager.com/gtag/js?id=${ANALYTICS_ID}`}
          />
          <Script id="google-analytics" strategy="afterInteractive">
            {`
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', '${ANALYTICS_ID}', { anonymize_ip: true });
            `}
          </Script>
        </>
      )}
      {consent === null && (
        <aside className="fs-consent" aria-label="Analytics preferences">
          <p>
            We use optional analytics to understand how people use this site.
            No analytics loads unless you allow it. <Link href="/privacy">Privacy details</Link>
          </p>
          <div>
            <button type="button" onClick={() => choose("declined")}>Decline</button>
            <button type="button" className="fs-consent-accept" onClick={() => choose("accepted")}>
              Allow analytics
            </button>
          </div>
        </aside>
      )}
    </>
  );
}

export function AnalyticsSettingsButton() {
  const reopen = () => {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Volatile state still lets the visitor change the current-page choice.
    }
    volatileConsent = null;
    const analyticsWindow = window as Window & {
      gtag?: (...args: unknown[]) => void;
    };
    analyticsWindow.gtag?.("consent", "update", {
      analytics_storage: "denied",
    });
    window.dispatchEvent(new Event(CONSENT_EVENT));
  };

  return <button type="button" onClick={reopen}>Analytics settings</button>;
}
