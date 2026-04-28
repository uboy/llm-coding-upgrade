import unittest

from env_template import TemplateResolutionError, resolve_templates


class TemplateResolverTests(unittest.TestCase):
    def test_plain_values_are_preserved(self):
        source = {"A": "alpha", "B": "beta"}
        result = resolve_templates(source)
        self.assertEqual(result, source)
        self.assertIsNot(result, source)

    def test_nested_references_are_resolved(self):
        source = {
            "HOST": "localhost",
            "PORT": "8080",
            "BASE": "http://${HOST}:${PORT}",
            "HEALTH": "${BASE}/health",
        }
        result = resolve_templates(source)
        self.assertEqual(result["HEALTH"], "http://localhost:8080/health")

    def test_default_is_used_for_missing_or_empty_value(self):
        source = {
            "REGION": "",
            "URL": "https://${REGION:-eu}.example.com",
            "FALLBACK_ONLY": "${MISSING:-default}",
        }
        result = resolve_templates(source)
        self.assertEqual(result["URL"], "https://eu.example.com")
        self.assertEqual(result["FALLBACK_ONLY"], "default")

    def test_dollar_escape_is_supported(self):
        source = {"PRICE": "$$5", "TEXT": "cost=$${VALUE:-7}"}
        result = resolve_templates(source)
        self.assertEqual(result["PRICE"], "$5")
        self.assertEqual(result["TEXT"], "cost=${VALUE:-7}")

    def test_missing_variable_raises(self):
        with self.assertRaises(TemplateResolutionError):
            resolve_templates({"URL": "https://${HOST}/api"})

    def test_cycle_raises(self):
        with self.assertRaises(TemplateResolutionError):
            resolve_templates({"A": "${B}", "B": "${C}", "C": "${A}"})


if __name__ == "__main__":
    unittest.main()
