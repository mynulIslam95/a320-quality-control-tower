"""Static frontend contract checks without third-party dependencies."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text()
JS = (ROOT / "app/static/app.js").read_text()
CSS = (ROOT / "app/static/style.css").read_text()


class FrontendContractTests(unittest.TestCase):
    def test_navigation_targets_exist(self):
        for name in ("overview", "explore", "aircraft", "requests"):
            with self.subTest(page=name):
                self.assertIn(f'id="{name}"', HTML)
                self.assertIn(f'data-page="{name}"', HTML)

    def test_javascript_element_references_exist(self):
        import re
        references = set(re.findall(r"\$\(['\"]([A-Za-z][A-Za-z0-9]*)['\"]\)", JS))
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        self.assertFalse(references - ids, f"Missing HTML elements: {references - ids}")

    def test_api_contracts_present(self):
        for endpoint in ("/api/analytics", "/api/aircraft/", "/api/requests", "/api/export"):
            with self.subTest(endpoint=endpoint):
                self.assertIn(endpoint, JS)

    def test_dashboard_assets_present(self):
        self.assertIn('src="/app.js"', HTML)
        self.assertIn('href="/style.css"', HTML)
        self.assertTrue(CSS.strip())
        self.assertIn('name="viewport"', HTML)

    def test_synthetic_data_disclaimer(self):
        self.assertIn("SYNTHETIC", HTML)
        self.assertIn("NOT AFFILIATED WITH AIRBUS", HTML)


if __name__ == "__main__":
    unittest.main()
