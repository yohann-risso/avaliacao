from django.test import SimpleTestCase
from django.test import Client

from .auth import verify_legacy_password
from .services import today_week_start


class LegacyAuthenticationTests(SimpleTestCase):
    def test_verifies_existing_pbkd2_hash_format(self):
        stored = "pbkdf2_sha256$1$73616c74$120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b"
        self.assertTrue(verify_legacy_password("password", stored))
        self.assertFalse(verify_legacy_password("wrong", stored))

    def test_week_start_is_monday(self):
        self.assertEqual(today_week_start().count("-"), 2)

    def test_login_page_renders_without_database_access(self):
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar no sistema")
