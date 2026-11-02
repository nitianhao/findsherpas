"""Upload a rendered HTML report to the findsherpas.com GitHub repo."""

from __future__ import annotations

import base64
import json
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_REPO = "nitianhao/findsherpas"
_BASE_URL = "https://findsherpas.com/report"
_DEFAULT_SLUGS_FILE = Path(__file__).resolve().parents[3] / "reports" / "report_slugs.json"

# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

_TLD_SUFFIX_RE = re.compile(
    r"_(?:co_[a-z]{2}|com_[a-z]{2}|com|net|org|io|cz|de|uk|fr|es|pl|at|nl|be|ch|se|dk|fi|no|pt|hu|ro|sk|si|ie|eu|us|ca|it)$"
)


def _company_slug(domain_slug: str) -> str:
    """Strip TLD suffix from a domain slug to get a clean company slug.

    'huckberry_com'     → 'huckberry'
    'www_zalando_de'    → 'zalando'
    'celiostore_cz'     → 'celiostore'
    'shop-apotheke_com' → 'shop_apotheke'   (hyphens and underscores are one separator)
    """
    slug = re.sub(r"^www_", "", domain_slug.lower())
    slug = slug.replace("-", "_")
    slug = _TLD_SUFFIX_RE.sub("", slug)
    return slug


class LegacyRegistryEntryError(RuntimeError):
    """The company key exists from before domains were recorded; ownership must be confirmed."""


def _registry_key(domain_slug: str, registry: dict, claim_legacy: bool = False) -> str:
    """Registry key for a domain: the bare company slug unless another market already owns it.

    zalando_de and zalando_ie strip to the same company slug. Re-publishing the second market
    under that key would overwrite the first market's live page — a URL a prospect may already
    have been emailed. Entries record the domain they were published for; when the bare key is
    taken by a *different* domain, this market gets a domain-qualified key instead.

    Entries published before domains were recorded carry none, so ownership cannot be inferred
    (bergzeit_at and bergzeit_de both map to "bergzeit"). Re-publishing over one requires
    ``claim_legacy=True``, which also records the domain so the question never comes up again.
    """
    company = _company_slug(domain_slug)
    domain = re.sub(r"^www_", "", domain_slug.lower()).replace("-", "_")
    entry = registry.get(company)
    if not isinstance(entry, dict):
        return company
    if entry.get("domain") is None:
        if claim_legacy:
            return company
        raise LegacyRegistryEntryError(
            f"registry entry '{company}' ({entry.get('url')}) predates domain tracking. If it is the "
            f"report for {domain}, re-publish with claim_legacy=True (orchestrator: --claim-legacy-slug); "
            f"if it belongs to another market, publish that market's domain first or edit the registry."
        )
    return company if entry["domain"] == domain else domain


def _load_slugs(path: Path = _DEFAULT_SLUGS_FILE) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _generate_report_slug(company: str, existing_slugs: set[str]) -> str:
    rng = random.SystemRandom()
    for _ in range(100):
        slug = f"{company}-{rng.randint(1000, 9999)}"
        if slug not in existing_slugs:
            return slug
    raise RuntimeError(f"Could not generate unique report slug for {company}")


def _report_slug(company: str, path: Path = _DEFAULT_SLUGS_FILE) -> str:
    """Existing slug for ``company`` from the local registry, or a new one (written locally)."""
    data = _load_slugs(path)
    slug, data = _assign_slug(company, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return slug


def _assign_slug(key: str, registry: dict, domain: str | None = None) -> tuple[str, dict]:
    """Return (slug, updated registry copy) for ``key``. Re-publishes reuse the existing slug."""
    data = dict(registry)
    existing = data.get(key, {})
    slug = existing.get("slug") if isinstance(existing, dict) else None
    if not (isinstance(slug, str) and slug):
        existing_slugs = {
            entry.get("slug")
            for entry in data.values()
            if isinstance(entry, dict) and isinstance(entry.get("slug"), str)
        }
        slug = _generate_report_slug(key, existing_slugs)
    entry = {"slug": slug, "url": f"{_BASE_URL}/{slug}/"}
    if domain:
        entry["domain"] = domain
    elif isinstance(existing, dict) and existing.get("domain"):
        entry["domain"] = existing["domain"]
    data[key] = entry
    return slug, data


def _merge_registries(remote: dict, local: dict) -> dict:
    """Remote registry wins for keys it has; local-only keys are kept.

    The local file can be stale (it was restored after a wipe), so pushing it verbatim would
    clobber entries that only exist in the repo. A ``domain`` recorded only locally is kept.
    """
    merged = dict(local)
    for key, entry in remote.items():
        local_entry = local.get(key)
        if (isinstance(entry, dict) and "domain" not in entry and isinstance(local_entry, dict)
                and local_entry.get("domain") and local_entry.get("slug") == entry.get("slug")):
            entry = {**entry, "domain": local_entry["domain"]}
        merged[key] = entry
    return merged


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

# The contents API only returns metadata for files over 1 MB when asked for the `object`
# media type; with the default type a re-publish of a large report gets no `sha` and the PUT
# fails with 422. Every published report with an embedded screenshot is over 1 MB.
_OBJECT_MEDIA_TYPE = "Accept: application/vnd.github.object"


def _gh_api(method: str, path: str, payload: dict | None = None, allow_404: bool = False) -> dict:
    cmd = ["gh", "api", "-X", method, path, "-H", _OBJECT_MEDIA_TYPE]
    if payload:
        cmd += ["--input", "-"]
    result = subprocess.run(
        cmd,
        input=json.dumps(payload).encode() if payload else None,
        capture_output=True,
    )
    if result.returncode != 0:
        if allow_404 and b"HTTP 404" in result.stderr:
            return {}
        raise RuntimeError(f"gh api failed: {result.stderr.decode()}")
    return json.loads(result.stdout) if result.stdout else {}


def _get_repo_json(repo_path: str) -> dict:
    """Decode a JSON file from the repo; {} when it does not exist yet."""
    existing = _gh_api("GET", f"/repos/{_REPO}/contents/{repo_path}", allow_404=True)
    content = existing.get("content") or ""
    if not content:
        return {}
    return json.loads(base64.b64decode(content).decode("utf-8"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _put_repo_file(repo_path: str, content_bytes: bytes, message: str) -> None:
    """Create or update a file in the findsherpas repo via the GitHub contents API."""
    api_path = f"/repos/{_REPO}/contents/{repo_path}"
    existing = _gh_api("GET", api_path, allow_404=True)
    sha = existing.get("sha")
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha
    _gh_api("PUT", api_path, payload)


@dataclass(frozen=True)
class PublishResult:
    company: str  # registry key the report is listed under
    slug: str
    url: str


def publish_report(
    html_content: str,
    domain_slug: str,
    slugs_file: Path = _DEFAULT_SLUGS_FILE,
    data_json: str | None = None,
    report_md: str | None = None,
    claim_legacy: bool = False,
) -> str:
    """Upload the report and return its unlisted URL. See :func:`publish_report_full`."""
    return publish_report_full(html_content, domain_slug, slugs_file, data_json, report_md, claim_legacy).url


def publish_report_full(
    html_content: str,
    domain_slug: str,
    slugs_file: Path = _DEFAULT_SLUGS_FILE,
    data_json: str | None = None,
    report_md: str | None = None,
    claim_legacy: bool = False,
) -> PublishResult:
    """Upload the report and return where it was published.

    Pushes to the repo (all via the GitHub contents API, which commits
    server-side and therefore bypasses the local `reports/*` gitignore):
      1. public/report/{slug}/index.html  → the live findsherpas.com page
      2. reports/report_slugs.json         → read by the CRM Reports page
      3. audit-data/{slug}/{slug}_data.json + _report.md (when provided)
         → version-controlled archive of the raw audit data so it survives a
           local wipe. NOT under public/ — never web-served.

    The registry MUST be committed to the repo, not just updated locally — the
    deployed CRM reads it from the repo, so a local-only update leaves the report
    invisible in the CRM.
    """
    registry = _merge_registries(_get_repo_json("reports/report_slugs.json"), _load_slugs(slugs_file))
    company = _registry_key(domain_slug, registry, claim_legacy=claim_legacy)
    domain = re.sub(r"^www_", "", domain_slug.lower()).replace("-", "_")
    report_slug, registry = _assign_slug(company, registry, domain=domain)
    registry_bytes = json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8")

    # 1. Report HTML → live page
    _put_repo_file(
        f"public/report/{report_slug}/index.html",
        html_content.encode("utf-8"),
        f"Add search audit report: {report_slug}",
    )

    # 2. Registry → CRM listing (push the merged registry the CRM reads from the repo), then
    #    mirror it locally only once the remote write succeeded.
    _put_repo_file(
        "reports/report_slugs.json",
        registry_bytes,
        f"Register search audit in report registry: {report_slug}",
    )
    slugs_file.parent.mkdir(parents=True, exist_ok=True)
    slugs_file.write_bytes(registry_bytes)

    # 3. Raw audit data → version-controlled archive (survives a local wipe).
    if data_json is not None:
        _put_repo_file(
            f"audit-data/{report_slug}/{report_slug}_data.json",
            data_json.encode("utf-8"),
            f"Archive raw audit data: {report_slug}",
        )
    if report_md is not None:
        _put_repo_file(
            f"audit-data/{report_slug}/{report_slug}_report.md",
            report_md.encode("utf-8"),
            f"Archive audit narrative: {report_slug}",
        )

    return PublishResult(company=company, slug=report_slug, url=f"{_BASE_URL}/{report_slug}/")
