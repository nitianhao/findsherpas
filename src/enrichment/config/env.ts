// ---------------------------------------------------------------------------
// Enrichment environment configuration
// ---------------------------------------------------------------------------

export type SearchProvider = "BRAVE" | "GOOGLE_BROWSER" | "BING_BROWSER";

export interface EnrichmentConfig {
  BRAVE_SEARCH_API_KEY: string | undefined;
  ENRICHMENT_SEARCH_PROVIDER: SearchProvider;
  ENRICHMENT_SEARCH_MAX_RESULTS: number;
}

export const config: EnrichmentConfig = {
  BRAVE_SEARCH_API_KEY: process.env.BRAVE_SEARCH_API_KEY,
  ENRICHMENT_SEARCH_PROVIDER:
    (process.env.ENRICHMENT_SEARCH_PROVIDER as SearchProvider) ?? "BRAVE",
  ENRICHMENT_SEARCH_MAX_RESULTS: Number(
    process.env.ENRICHMENT_SEARCH_MAX_RESULTS ?? "8",
  ),
};

/**
 * Throws a clear error if the Brave API key is not configured.
 */
export function assertBraveApiKey(): string {
  const key = config.BRAVE_SEARCH_API_KEY;
  if (!key || key.trim().length === 0) {
    throw new Error(
      [
        "",
        "=== BRAVE_SEARCH_API_KEY is not set ===",
        "",
        "The enrichment pipeline requires a Brave Search API key.",
        "",
        "1. Sign up at https://brave.com/search/api/ (free tier: 2 000 queries/month)",
        "2. Create an API key in the Brave Search dashboard",
        "3. Export it in your shell before running the script:",
        "",
        "   export BRAVE_SEARCH_API_KEY=\"BSA...your-key-here\"",
        "",
        "Or add it to your .env.local / .zshrc for persistence.",
        "",
      ].join("\n"),
    );
  }
  return key.trim();
}
