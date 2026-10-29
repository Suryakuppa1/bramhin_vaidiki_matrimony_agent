import tempfile
import unittest
from pathlib import Path

import vault.db as vault_db
from vault.ingest import ingest_inbox, ingest_text
from vault.parser import parse_vault_profile
from vault.search import search_profiles


SAMPLE = """CONSENT:YES
Gender: Male
Name: SARVEPALLI VENKATESH BABU
Father name: SREE HARI RAO SARVEPALLI
Mothername: MADHAVI SARVEPALLI
DOB: 30-07-1995
Nakshatram: Maka, 4 PADAM
Rashi: SIMHA
Place of Birth: VIJAYAWADA
Education: B. TECH. (Civil)
ContactNumber: 9391073474, 6281790680, 9491728910
"""


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = vault_db.DB_PATH
        vault_db.DB_PATH = Path(self.tmp.name) / "vault.sqlite3"
        self.inbox = Path(self.tmp.name) / "inbox"
        self.inbox.mkdir()

    def tearDown(self):
        vault_db.DB_PATH = self.old
        self.tmp.cleanup()

    def test_parse_keeps_phone_and_maka_padam(self):
        p = parse_vault_profile(SAMPLE)
        self.assertIsNotNone(p)
        self.assertEqual(p["gender"], "male")
        self.assertEqual(p["nakshatram"], "magha")
        self.assertEqual(p["padam"], "4")
        self.assertEqual(p["rashi"], "simha")
        self.assertIn("9391073474", p["phone"])

    def test_ingest_and_search_full_details(self):
        yes, skipped = ingest_text(SAMPLE, source_file="sample.txt", source_kind="text")
        self.assertEqual(yes, 1)
        rows = search_profiles(stars="Maka", padam="4", gender="Male", phone="93910")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "SARVEPALLI VENKATESH BABU")
        self.assertIn("9391073474", rows[0]["phone"])
        self.assertIn("SREE HARI", rows[0]["father_name"])

    def test_inbox_ingest(self):
        (self.inbox / "one.txt").write_text(SAMPLE, encoding="utf-8")
        stats = ingest_inbox(self.inbox, permission_confirmed=True)
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(vault_db.count_profiles(), 1)
        with self.assertRaises(ValueError):
            ingest_inbox(self.inbox, permission_confirmed=False)


if __name__ == "__main__":
    unittest.main()
