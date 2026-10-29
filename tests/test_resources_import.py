import tempfile
import unittest
from pathlib import Path
from unittest import mock

import core
from core import (
    import_resources_dir,
    import_text_export,
    load_profiles,
    split_profile_blocks,
    strip_chat_prefixes,
)
from preferences import matching_rows


SAMPLE = """CONSENT:YES
Name: Ananya
DOB: 14-07-1999
Nakshatram: Rohini
Rashi: Vrishabha
Place of Birth: Vijayawada
Education: B.Tech
"""

WHATSAPP = """12/10/26, 9:15 am - Aunt: CONSENT:YES
12/10/26, 9:15 am - Aunt: Name: Ananya
12/10/26, 9:15 am - Aunt: DOB: 14-07-1999
12/10/26, 9:15 am - Aunt: Nakshatram: Rohini
12/10/26, 9:15 am - Aunt: Place of Birth: Vijayawada
12/10/26, 9:15 am - Aunt: Education: B.Tech
"""


class ResourcesImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = core.DB_PATH
        core.DB_PATH = Path(self.tmp.name) / "profiles.sqlite3"
        self.resources = Path(self.tmp.name) / "resources"
        self.resources.mkdir()

    def tearDown(self):
        core.DB_PATH = self.old
        self.tmp.cleanup()

    def test_strip_whatsapp_prefix(self):
        cleaned = strip_chat_prefixes(WHATSAPP)
        self.assertIn("Name: Ananya", cleaned)
        self.assertNotIn("Aunt:", cleaned)

    def test_split_consent_blocks(self):
        text = SAMPLE + "\n\nCONSENT:YES\nName: Bhavana\nDOB: 01-01-2000\nNakshatram: Swathi\nEducation: MBA\n"
        blocks = split_profile_blocks(text)
        self.assertGreaterEqual(len(blocks), 2)

    def test_import_text_and_match(self):
        yes, skipped = import_text_export(SAMPLE, filename="group_a.txt", permission_confirmed=True)
        self.assertEqual(yes, 1)
        self.assertEqual(skipped, 0)
        rows = matching_rows(
            load_profiles(),
            dict(min_age=20, max_age=30, stars="Rohini", birthplace="", rashi="", education="",
                 dob_start=None, dob_end=None, group=""),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Ananya")

    def test_whatsapp_export_import(self):
        yes, _ = import_text_export(WHATSAPP, filename="wa.txt", permission_confirmed=True)
        self.assertEqual(yes, 1)

    def test_resources_dir_skips_images(self):
        (self.resources / "ok.txt").write_text(SAMPLE, encoding="utf-8")
        (self.resources / "photo.jpg").write_bytes(b"not-an-image")
        stats = import_resources_dir(self.resources, permission_confirmed=True)
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(stats["ignored_media"], 1)
        self.assertEqual(stats["files"], 1)

    def test_requires_permission(self):
        with self.assertRaises(ValueError):
            import_text_export(SAMPLE, filename="x.txt", permission_confirmed=False)


if __name__ == "__main__":
    unittest.main()
