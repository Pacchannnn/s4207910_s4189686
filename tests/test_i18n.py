import unittest
from immunisation_app import create_app
from immunisation_app.i18n import CATALOGS, LANGUAGES


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_all_languages_render_and_translate_navigation(self):
        for code in LANGUAGES:
            response = self.client.get("/language", query_string={"language": code, "next": "/"})
            self.assertEqual(response.status_code, 303)
            for path in ("/", "/mission", "/vaccinations", "/infections", "/improvements", "/benchmark"):
                page = self.client.get(path)
                self.assertEqual(page.status_code, 200)
                text = page.get_data(as_text=True)
                self.assertIn(CATALOGS[code]["Overview"], text)
                self.assertIn('lang="' + ("zh-Hans" if code == "zh" else code) + '"', text)
                self.assertNotIn("<script", text)

    def test_filters_and_cookie_are_preserved(self):
        target = "/vaccinations?antigen=RCV1&year=2000&minimum=90"
        response = self.client.get("/language", query_string={"language": "vi", "next": target})
        self.assertEqual(response.location, target)
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        page = self.client.get(target).get_data(as_text=True)
        self.assertIn("Singapore", page)
        self.assertIn("Malta", page)
        self.assertIn("Áp dụng bộ lọc", page)
        self.assertIn("Tiêm chủng", self.client.get("/mission").get_data(as_text=True))

    def test_invalid_language_and_redirects_rejected(self):
        for args in ({"language": "xx"}, {"language": "vi", "next": "//evil.test"},
                     {"language": "vi", "next": "https://evil.test"},
                     {"language": "vi", "next": "/unknown"}):
            self.assertEqual(self.client.get("/language", query_string=args).status_code, 400)

    def test_invalid_cookie_falls_back_to_english(self):
        self.client.set_cookie("atlas_language", "invalid")
        self.assertIn('lang="en"', self.client.get("/").get_data(as_text=True))
