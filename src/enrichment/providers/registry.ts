// ---------------------------------------------------------------------------
// Provider registry. Maps provider names → implementations and resolves the
// ordered, enabled provider list from config.
// ---------------------------------------------------------------------------

import type { EmailEnrichmentProvider, ProviderName } from "./types";
import { hunterProvider } from "./hunterProvider";
import { apolloProvider } from "./apolloProvider";
import { prospeoProvider } from "./prospeoProvider";
import { findymailProvider } from "./findymailProvider";
import { dropcontactProvider } from "./dropcontactProvider";
import { inferenceProvider } from "./inferenceProvider";
import { loadWaterfallConfig } from "./config";

export const PROVIDER_REGISTRY: Record<ProviderName, EmailEnrichmentProvider> = {
  hunter: hunterProvider,
  prospeo: prospeoProvider,
  findymail: findymailProvider,
  dropcontact: dropcontactProvider,
  apollo: apolloProvider,
  inference: inferenceProvider,
};

export function getProvider(name: ProviderName): EmailEnrichmentProvider {
  return PROVIDER_REGISTRY[name];
}

/**
 * The providers to run, in waterfall order, filtered to those with a key.
 * Pass `includeDisabled` to keep stubs (used by the comparison tool so it can
 * report "disabled" rows).
 */
export function resolveProviders(opts: { includeDisabled?: boolean } = {}): EmailEnrichmentProvider[] {
  const cfg = loadWaterfallConfig();
  return cfg.order
    .map((n) => PROVIDER_REGISTRY[n])
    .filter((p) => opts.includeDisabled || p.isEnabled());
}
