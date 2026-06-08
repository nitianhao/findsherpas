"""Upload a rendered HTML report to the findsherpas.com GitHub repo."""

from __future__ import annotations

import base64
import json
import random
import re
import subprocess
from pathlib import Path

_REPO = "nitianhao/findsherpas"
_BASE_URL = "https://findsherpas.com/report"
_DEFAULT_SLUGS_FILE = Path(__file__).resolve().parents[3] / "reports" / "report_slugs.json"

# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _company_slug(domain_slug: str) -> str:
    """Strip TLD suffix from a domain slug to get a clean company slug.

    'huckberry_com'     → 'huckberry'
    'www_zalando_de'    → 'zalando'
    'celiostore_cz'     → 'celiostore'
    """
    slug = re.sub(r"^www_", "", domain_slug)
    slug = re.sub(r"_(?:com|net|org|io|co_\w+|cz|de|uk|fr|es|pl|at|nl|be|ch|se|dk|fi|no|pt|hu|ro|sk|si|ie|eu|us|ca|it)$", "", slug)
    return slug


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
    data = _load_slugs(path)
    existing = data.get(company, {})
    slug = existing.get("slug")
    if isinstance(slug, str) and slug:
        return slug

    existing_slugs = {
        entry.get("slug")
        for entry in data.values()
        if isinstance(entry, dict) and isinstance(entry.get("slug"), str)
    }
    slug = _generate_report_slug(company, existing_slugs)
    data[company] = {
        "slug": slug,
        "url": f"{_BASE_URL}/{slug}/",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return slug


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def _gh_api(method: str, path: str, payload: dict | None = None, allow_404: bool = False) -> dict:
    cmd = ["gh", "api", "-X", method, path]
    if payload:
        cmd += ["--input", "-"]
    result = subprocess.run(
        cmd,
        input=json.dumps(payload).encode() if payload else None,
        capture_output=True,
    )
    if result.returncode != 0:
        if allow_404 and b"Not Found" in result.stderr:
            return {}
        raise RuntimeError(f"gh api failed: {result.stderr.decode()}")
    return json.loads(result.stdout) if result.stdout else {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def publish_report(
    html_content: str,
    domain_slug: str,
    slugs_file: Path = _DEFAULT_SLUGS_FILE,
) -> str:
    """Upload the report and return its unlisted URL."""
    company = _company_slug(domain_slug)
    report_slug = _report_slug(company, slugs_file)

    repo_path = f"public/report/{report_slug}/index.html"
    api_path = f"/repos/{_REPO}/contents/{repo_path}"

    existing = _gh_api("GET", api_path, allow_404=True)
    sha = existing.get("sha")

    payload = {
        "message": f"{'Update' if sha else 'Add'} search audit report: {report_slug}",
        "content": base64.b64encode(html_content.encode("utf-8")).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    _gh_api("PUT", api_path, payload)
    url = f"{_BASE_URL}/{report_slug}/"
    return url
