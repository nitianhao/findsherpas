# Report Publishing & CRM Writeback — Notes

> **Status: MIGRATED & UNRECONCILED.** This content was moved out of the website
> `README.md` on 2026-06-08 so audit documentation lives with the audit pipeline.
> It has **not** been verified against the current code. Known conflicts to resolve
> during audit-doc reconciliation:
> - This doc says reports publish to `https://findsherpas.com/report/{company}-1234/`
>   and write a `{slug}_access.json`. The `synthetic-search-audit` skill instead
>   describes a password gate + `reports/passwords.json` and a different slug format.
>   Verify against `src/audit/src/github_publisher.py` before treating either as canonical.

---

## Search audit reports
- Audit engine: `src/audit/`
- Default report output: `reports/`
- Legacy audit utilities migrated from the discontinued audit workspace: `src/audit/scripts/`

New audit runs should be created from this repo. The audit orchestrator defaults to the top-level `reports/` directory.

When an audit is published, the orchestrator uploads the unlisted HTML report to a non-guessable URL like `https://findsherpas.com/report/{company}-1234/`. Report slugs are stored in `reports/report_slugs.json` so future republishes keep the same URL. The orchestrator also writes a `{slug}_access.json` file next to the report artifacts with:
- `report_url`
- `published_at`

If the audited company already exists in CRM, pass its InstantDB company id so the report URL and audit personalization variables are written immediately:

```bash
python3 src/audit/src/orchestrator.py "https://example.com/search?q=shoes" \
  --crm-company-id <instantdb-company-id>
```

For an existing report artifact, write the same fields manually with:

```bash
npx tsx --tsconfig tsconfig.json src/enrichment/scripts/writeAuditToCRM.ts \
  --company-id <instantdb-company-id> \
  --report reports/example/example_YYYYMMDD_HHMMSS_data.json \
  --report-url https://findsherpas.com/report/example/
```

CRM email sequences use company-level audit variables from this writeback, including `{{score}}`, `{{query_count}}`, `{{top_3_rate}}`, `{{outside_3_rate}}`, `{{worst_query}}`, `{{worst_pos}}`, `{{wrong_product}}`, `{{search_platform_sentence}}`, and `{{report_url}}`. `{{query_count}}` is derived from the actual number of query judgments in the report, so sequence copy can vary by audit size. `{{search_platform_sentence}}` is intentionally cautious and currently renders as `Looks fixable without replatforming.`

Generated HTML audit reports must show the Find Sherpas logo and wordmark on the cover. Keep the cover logo block in `src/audit/templates/master_report.html`, and keep the SVG asset at `src/audit/assets/logo.svg`; reports should not be shipped if that branding is missing.

Current report presentation rules:
- The reusable HTML template is `src/audit/templates/master_report.html`.
- The cover should feel like a boutique agency presentation: large Find Sherpas logo/wordmark, clean client name line, and a separate `Prepared by` block with `Name`, `Agency`, and `Contact`.
- Do not put `findsherpas.com` inside the logo/wordmark lockup. Put it in the `Prepared by` block as the agency link.
- Do not include a methodology/process section in client-facing reports. Avoid exposing automation, scoring pipeline, scraper, LLM, or implementation details in the rendered report.
- Keep the short-version summary, revenue-risk hero, tier cards, coverage heatmap, revenue-risk failure cards, deep dives, appendix, scope/boundaries section, and final CTA.
- The final CTA must link to the live Find Sherpas booking flow: `https://findsherpas.com/book-a-call`.
