import unittest
from immunisation_app import create_app


class OverviewPresentationTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_plain_brand_and_compact_footer(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Vaccination &amp; Disease Data", page)
        self.assertNotIn("Immunisation Atlas", page)
        self.assertIn("s4207910 &amp; s4189686", page)
        self.assertNotIn("See the story behind", page)

    def test_mission_uses_unit_reference_instead_of_photo(self):
        page = self.client.get("/mission").get_data(as_text=True)
        self.assertIn("What the numbers mean", page)
        self.assertIn("Example user profiles", page)
        self.assertNotIn("immunisation-hero.png", page)
        self.assertNotIn("These personas were supplied", page)
        self.assertNotIn("Unvalidated draft", page)
        self.assertNotIn("person.provenance", page)
