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
2. Run `publish_report(html, '{domain_slug}')` — one call pushes BOTH the findsherpas.com
   page and the CRM registry entry.
3. **Verify the REPO copy**, not just local (commands below).
4. After any publish issue, record the cause and fix.

---

## General learnings (apply to every audit)

- **One call, two files.** `publish_report` uploads the HTML to
  `public/report/{report_slug}/index.html` AND updates `reports/report_slugs.json`, then
  pushes both to `nitianhao/findsherpas`. A local-only registry update is invisible in the
  CRM — the deployed page reads `report_slugs.json` **from the repo**.
- **CRM company key** = domain slug minus `www_` and TLD.
- **Verify against the repo:**
  - `gh api /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the `{company}` entry.
  - `gh api /repos/nitianhao/findsherpas/contents/public/report/{report_slug}/index.html --jq '.size'` matches the local HTML byte size.
- **Redeploy lag:** the CRM row appears after the Vercel redeploy (~1–2 min) the push triggers.
- Phase 8 is mandatory — an audit isn't done until the report is live AND registered.

---

## Per-site profiles

_(none yet — add an entry only for hosts with a non-obvious slug or a publish quirk)_

---

## When you learn something new

After any Phase 8 issue, append the cause/fix here (slug surprises, auth/visibility
problems, redeploy gotchas).
