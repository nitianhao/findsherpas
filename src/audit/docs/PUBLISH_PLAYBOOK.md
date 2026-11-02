# Publish Playbook — Phase 8 knowledge base

> **Read this BEFORE running Phase 8 (`publish_report`).** It records publishing/registry
> conventions and gotchas, so we don't re-trip the same slug and visibility issues each
> audit. When something goes wrong in publish, capture it here.
>
> Companion docs: `ARCHITECTURE.md` and the `synthetic-search-audit` skill. Operational
> memory for the **publish** phase. See also project memory "Audit Phase 8 publish".

---

## How to use this file

1. Before Phase 8, read **General learnings** and any **Per-site profile** (e.g. an
   unusual slug). Confirm `gh auth status` is the repo owner.
2. Run the publish gate (`python -m src.publish_gate <data.json> --html <report.html>`). Only
   when it passes, run `publish_report_full(html, '{domain_slug}', data_json=..., report_md=...)`
   — one call pushes the findsherpas.com page, the CRM registry entry and the raw-data archive.
3. **Verify the REPO copy**, not just local (commands below).
4. After any publish issue, record the cause and fix.

---

## General learnings (apply to every audit)

- **One call, up to four files.** `publish_report_full` uploads the HTML to
  `public/report/{report_slug}/index.html`, the merged `reports/report_slugs.json`, and (when
  passed) `audit-data/{report_slug}/{report_slug}_data.json` + `_report.md`. A local-only
  registry update is invisible in the CRM — the deployed page reads `report_slugs.json`
  **from the repo**.
- **Registry merge (2026-10-30).** The local `reports/report_slugs.json` was restored after a
  wipe and can be stale. Publishing now fetches the repo registry first and merges (remote
  wins), so pushing can no longer drop repo-only entries; the local copy is only rewritten
  after the remote push succeeds.
- **CRM company key** = domain slug minus `www_` and TLD (hyphens → underscores). Entries now
  record their `domain`; a second market of the same company (`zalando_ie` after
  `zalando_de`) gets a domain-qualified key instead of overwriting the first market's live page.
- **Reports over 1 MB.** The contents API only returns a file's `sha` for files over 1 MB with
  the `object` media type — without it a re-publish fails with 422. `_gh_api` always sends
  `Accept: application/vnd.github.object`. The renderer now re-encodes the cover screenshot so
  new reports are ~160–280 KB.
- **Verify against the repo:**
  - `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the `{company}` entry.
  - `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/public/report/{report_slug}/index.html --jq '.size'` matches the local HTML byte size.
- **Client-visible text (2026-10-30).** All 14 reports published before this date show raw
  relevance numbers ("relevance 0.703") to the prospect. The gate now blocks that; re-publish
  old reports only after regenerating them through the current pipeline.
- **Redeploy lag:** the CRM row appears after the Vercel redeploy (~1–2 min) the push triggers.
- Phase 8 is mandatory — an audit isn't done until the report is live AND registered.

---

## Per-site profiles

_(none yet — add an entry only for hosts with a non-obvious slug or a publish quirk)_

---

## When you learn something new

After any Phase 8 issue, append the cause/fix here (slug surprises, auth/visibility
problems, redeploy gotchas).
