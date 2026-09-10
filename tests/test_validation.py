import unittest

from immunisation_app.validation import parse_int, valid_scalar


class ValidationTests(unittest.TestCase):
    def test_parse_int_uses_default_only_when_value_is_missing(self):
        self.assertEqual(parse_int(None, 2024, "Year"), (2024, None))

    def test_parse_int_reports_malformed_value(self):
        self.assertEqual(
            parse_int("twenty", 2024, "Year"),
            (2024, "Year must be a whole number."),
        )

    def test_valid_scalar_uses_an_explicit_whitelist(self):
        self.assertTrue(valid_scalar("rate", {"rate", "country"}))
        self.assertFalse(
            valid_scalar("rate; DROP TABLE Country;", {"rate", "country"})
        )
