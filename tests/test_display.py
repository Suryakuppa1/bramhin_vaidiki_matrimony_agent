import unittest
from display import (
    format_profile_text,
    format_matches_list,
    format_profile_html,
    profile_rows,
    profile_sections,
)


SAMPLE = {
    "name": "SARVEPALLI VENKATESH BABU",
    "gender": "male",
    "father_name": "SREE HARI RAO SARVEPALLI",
    "mother_name": "MADHAVI SARVEPALLI",
    "dob": "1995-07-30",
    "age": 31,
    "nakshatram": "magha",
    "padam": "4",
    "rashi": "simha",
    "birthplace": "vijayawada",
    "education": "B. TECH. (Civil)",
    "phone": "9391073474, 6281790680",
    "source_file": "sample.txt",
}


class DisplayTests(unittest.TestCase):
    def test_telegram_block_readable(self):
        text = format_profile_text(SAMPLE, index=1, include_phone=False)
        self.assertIn("1. SARVEPALLI VENKATESH BABU", text)
        self.assertIn("Personal", text)
        self.assertIn("Family", text)
        self.assertIn("Astrology", text)
        self.assertIn("Gender: Male", text)
        self.assertIn("Age / DOB: 31 yrs", text)
        self.assertIn("30 Jul 1995", text)
        self.assertIn("Nakshatram: Magha  ·  Padam 4", text)
        self.assertIn("Rashi: Simha", text)
        self.assertIn("Birthplace: Vijayawada", text)
        self.assertNotIn("9391073474", text)

    def test_vault_html_includes_phone(self):
        html = format_profile_html(SAMPLE, index=1, include_phone=True)
        self.assertIn("9391073474", html)
        self.assertIn("Father", html)
        self.assertIn("Nakshatram", html)
        self.assertIn("mv-sheet", html)
        self.assertIn("Personal", html)

    def test_chunks_under_limit(self):
        rows = [dict(SAMPLE, name=f"Person {i}") for i in range(6)]
        chunks = format_matches_list(rows, header="Found 6", include_phone=False, limit=6)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(len(c) < 4096 for c in chunks))

    def test_phone_row_optional(self):
        labels = [label for label, _ in profile_rows(SAMPLE, include_phone=True)]
        self.assertIn("Phone", labels)
        labels2 = [label for label, _ in profile_rows(SAMPLE, include_phone=False)]
        self.assertNotIn("Phone", labels2)

    def test_sections_group_fields(self):
        sections = dict(profile_sections(SAMPLE, include_phone=True))
        self.assertIn("Personal", sections)
        self.assertIn("Family", sections)
        phone_labels = [lab for lab, _ in sections["Family"]]
        self.assertIn("Phone", phone_labels)


if __name__ == "__main__":
    unittest.main()
