import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import github_publisher as gp


class SlugTests(unittest.TestCase):
    def test_company_slug_table(self):
        self.assertEqual(gp._company_slug("huckberry_com"), "huckberry")
        self.assertEqual(gp._company_slug("www_zalando_de"), "zalando")
        self.assertEqual(gp._company_slug("cotswoldoutdoor_co_uk"), "cotswoldoutdoor")
        self.assertEqual(gp._company_slug("www_shop-apotheke_com"), "shop_apotheke")
        self.assertEqual(gp._company_slug("baechli_bergsport_ch"), "baechli_bergsport")
        # co_ followed by a long label is not a TLD pair and must not be stripped
        self.assertEqual(gp._company_slug("acme_co_shop"), "acme_co_shop")

    def test_second_market_does_not_overwrite_first(self):
        registry = {"zalando": {"slug": "zalando-1111", "url": "u", "domain": "zalando_de"}}
        self.assertEqual(gp._registry_key("www_zalando_de", registry), "zalando")
        self.assertEqual(gp._registry_key("zalando_ie", registry), "zalando_ie")

    def test_legacy_entry_without_domain_needs_explicit_claim(self):
        registry = {"bergzeit": {"slug": "bergzeit-3913", "url": "u"}}
        with self.assertRaises(gp.LegacyRegistryEntryError):
            gp._registry_key("bergzeit_at", registry)
        self.assertEqual(gp._registry_key("bergzeit_de", registry, claim_legacy=True), "bergzeit")
        registry = {"huckberry": {"slug": "huckberry-8361", "url": "u"}}
        slug, _ = gp._assign_slug("huckberry", registry, domain="huckberry_com")
        self.assertEqual(slug, "huckberry-8361")


class MergeTests(unittest.TestCase):
    def test_local_domain_fills_remote_legacy_entry(self):
        remote = {"lyko": {"slug": "lyko-6587", "url": "x"}}
        local = {"lyko": {"slug": "lyko-6587", "url": "x", "domain": "lyko_se"}}
        self.assertEqual(gp._merge_registries(remote, local)["lyko"]["domain"], "lyko_se")


class PublishTests(unittest.TestCase):
    def _run(self, remote_registry: dict, local_registry: dict, fail_on: str | None = None):
        calls = []

        def fake_api(method, path, payload=None, allow_404=False):
            calls.append((method, path, payload))
            if method == "GET" and path.endswith("reports/report_slugs.json"):
                if not remote_registry:
                    return {}
                return {"sha": "abc", "content": base64.b64encode(json.dumps(remote_registry).encode()).decode()}
            if method == "GET":
                return {}
            if fail_on and fail_on in path:
                raise RuntimeError("boom")
            return {}

        tmp = Path(tempfile.mkdtemp()) / "report_slugs.json"
        tmp.write_text(json.dumps(local_registry))
        with mock.patch.object(gp, "_gh_api", side_effect=fake_api):
            try:
                result = gp.publish_report_full("<html/>", "huckberry_com", slugs_file=tmp, data_json="{}",
                                                claim_legacy=True)
            except RuntimeError:
                result = None
        return result, calls, json.loads(tmp.read_text())

    def test_remote_registry_entries_survive(self):
        remote = {"lyko": {"slug": "lyko-6587", "url": "x"}}
        result, calls, local_after = self._run(remote, {"huckberry": {"slug": "huckberry-8361", "url": "y"}})
        self.assertEqual(result.slug, "huckberry-8361")
        pushed = [p for m, path, p in calls if m == "PUT" and path.endswith("report_slugs.json")][0]
        pushed_registry = json.loads(base64.b64decode(pushed["content"]))
        self.assertIn("lyko", pushed_registry)
        self.assertEqual(pushed_registry["huckberry"]["domain"], "huckberry_com")
        self.assertIn("lyko", local_after)

    def test_local_registry_untouched_when_upload_fails(self):
        local = {"other": {"slug": "other-1", "url": "z"}}
        result, _, local_after = self._run({}, local, fail_on="public/report")
        self.assertIsNone(result)
        self.assertEqual(local_after, local)

    def test_existing_sha_is_sent_on_update(self):
        def fake_api(method, path, payload=None, allow_404=False):
            if method == "GET":
                return {"sha": "deadbeef"}
            fake_api.put = payload
            return {}
        with mock.patch.object(gp, "_gh_api", side_effect=fake_api):
            gp._put_repo_file("public/report/x/index.html", b"<html/>", "msg")
        self.assertEqual(fake_api.put["sha"], "deadbeef")


if __name__ == "__main__":
    unittest.main()
