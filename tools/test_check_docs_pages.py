"""Offline regression fixtures for the documentation build checker."""

import tempfile
import unittest
from pathlib import Path

from check_docs_pages import check_build


class DocsBuildLinksTests(unittest.TestCase):
    def test_local_reference_contract(self):
        cases = [
            ("valid", '<link href="/dcc-mcp-maya/assets/app.css"><a href="./next.html">Next</a>', False),
            ("root asset", '<script src="/assets/app.js"></script>', True),
            ("missing asset", '<img src="/dcc-mcp-maya/missing.png">', True),
            ("missing navigation", '<a href="/dcc-mcp-maya/missing.html">Bad</a>', True),
            ("relative escape", '<a href="../../outside.html">Bad</a>', True),
            ("encoded escape", '<a href="/dcc-mcp-maya/%2e%2e/outside.html">Bad</a>', True),
            ("external only", '<a href="https://example.invalid/"><img src="data:image/png;base64,AA==">', True),
            (
                "escaped code",
                '<pre>&lt;img src="/missing.png"&gt;</pre><link href="/dcc-mcp-maya/assets/app.css">',
                False,
            ),
        ]
        for name, html, should_fail in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                dist = Path(directory)
                (dist / "assets").mkdir()
                (dist / "assets/app.css").write_text("body {}", encoding="utf-8")
                (dist / "index.html").write_text(html, encoding="utf-8")
                (dist / "next.html").write_text('<a href="#ok">anchor</a>', encoding="utf-8")
                pages, checked, errors = check_build(dist, "/dcc-mcp-maya/")
                self.assertEqual(pages, 2)
                self.assertEqual(bool(errors), should_fail, errors)
                if not should_fail:
                    self.assertGreater(checked, 0)

    def test_empty_build_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            pages, checked, errors = check_build(Path(directory), "/dcc-mcp-maya/")
            self.assertEqual((pages, checked), (0, 0))
            self.assertTrue(errors)

    def test_explicit_root_base_is_supported(self):
        # Generic callers may use a root deployment. CI uses the project default.
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / "index.html").write_text('<link href="/style.css">', encoding="utf-8")
            (dist / "style.css").write_text("body {}", encoding="utf-8")
            self.assertEqual(check_build(dist, "/"), (1, 1, []))


if __name__ == "__main__":
    unittest.main()
