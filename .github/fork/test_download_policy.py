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
        self.assertEqual(method_body(self.original, "checkMachineIsChinaMainland"),
                         method_body(normalized, "checkMachineIsChinaMainland"))
        verify(self.root)

    def test_reapplies_to_network_restriction(self):
        upstream = render_region(self.original).replace("return false;\n    }\n\n    /// Prevents", "return true;\n    }\n\n    /// Prevents")
        self.assertIn("return false;", method_body(render_region(upstream), "isIsChinaMainlandNetwork"))

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
