#!/usr/bin/env python3
"""Regression coverage for upstream rewrites, idempotency and restriction drift."""

from pathlib import Path
import tempfile
import unittest

from download_policy import REGION, render_region, verify, method_body


class DownloadPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = Path.cwd() / REGION
        self.original = self.source.read_text(encoding="utf-8")
        (self.root / REGION).parent.mkdir(parents=True)
        self.write(render_region(self.original))

    def write(self, text):
        (self.root / REGION).write_text(text, encoding="utf-8")

    def test_idempotent_and_preserves_machine_detection(self):
        normalized = render_region(self.original)
        self.assertEqual(normalized, render_region(normalized))
        self.assertEqual(method_body(self.original, "checkMachineIsChinaMainland").replace("@Nullable ", ""),
                         method_body(normalized, "checkMachineIsChinaMainland").replace("@Nullable ", ""))
        verify(self.root)

    def test_reapplies_to_network_restriction(self):
        upstream = render_region(self.original).replace("return false;\n    }\n\n    /// Prevents", "return true;\n    }\n\n    /// Prevents")
        self.assertIn("return false;", method_body(render_region(upstream), "isIsChinaMainlandNetwork"))

    def test_removes_network_query_cache_and_startup_task(self):
        upstream = render_region(self.original).replace(
            "// This fork never queries the user's public IP to restrict downloads.",
            "Schedulers.io().execute(RegionUtils::isIsChinaMainlandNetwork);",
        ).replace(
            "public final class RegionUtils {",
            'public final class RegionUtils {\n'
            'private static volatile Boolean isChinaMainlandNetwork;\n'
            'private static boolean checkChinaMainlandNetwork() {\n'
            'NetworkUtils.doGet("https://ipwho.is"); return true;\n}\n',
        )
        normalized = render_region(upstream)
        self.assertNotIn("ipwho.is", normalized)
        self.assertNotIn("Schedulers", normalized)
        self.assertNotIn("volatile", normalized)
        self.assertEqual("", method_body(normalized, "init").split("//")[0].strip())
        self.write(normalized)
        verify(self.root)

    def test_parser_ignores_braces_in_comments_and_literals(self):
        upstream = render_region(self.original).replace(
            'private static boolean checkMachineIsChinaMainland() {',
            'private static boolean checkMachineIsChinaMainland() {\n'
            '// A comment containing } and {\n'
            'String braces = "} {";\n',
        )
        normalized = render_region(upstream)
        self.assertIn('String braces = "} {";', normalized)
        self.write(normalized)
        verify(self.root)

    def test_detects_modified_policy(self):
        normalized = render_region(self.original)
        self.write(normalized.replace("return false;\n    }\n\n    /// Prevents", "return true;\n    }\n\n    /// Prevents"))
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_unknown_region_api_requires_review(self):
        extra = self.original.replace("public final class RegionUtils {", "public final class RegionUtils {\npublic static boolean isRestricted() { return true; }")
        with self.assertRaises(ValueError):
            render_region(extra)

    def test_new_restriction_caller_requires_review(self):
        path = self.root / "HMCL/src/main/java/Unexpected.java"
        path.write_text("class Unexpected { boolean blocked = RegionUtils.isIsChinaMainlandNetwork(); }")
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_inverted_ui_condition_requires_review(self):
        path = self.root / "HMCL/src/main/java/org/jackhuang/hmcl/ui/download/VersionsPage.java"
        path.parent.mkdir(parents=True)
        path.write_text("if (!RegionUtils.isIsChinaMainlandNetwork()) {")
        with self.assertRaises(ValueError):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
