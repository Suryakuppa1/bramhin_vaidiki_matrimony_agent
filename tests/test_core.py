import unittest
from datetime import date
from core import parse_profile, is_match, get_age, normalized_star

SAMPLE = """Bride Profile
Name: Ananya
DOB: 14-07-1999
Nakshatram: Rohini
Rashi: Vrishabha
Place of Birth: Vijayawada
Education: B.Tech
"""

class CoreTests(unittest.TestCase):
    def test_extraction(self):
        p = parse_profile(SAMPLE)
        self.assertEqual(p["name"], "Ananya")
        self.assertEqual(p["dob"], "1999-07-14")
        self.assertEqual(p["nakshatram"], "rohini")
        self.assertEqual(p["birthplace"], "Vijayawada")
    def test_match(self):
        p = parse_profile(SAMPLE)
        self.assertEqual(is_match(p, min_age=25, max_age=29, stars="రోహిణి", birthplace="Vijayawada"), "Match")
        self.assertEqual(is_match(p, stars="Swathi"), "No match")
    def test_missing(self):
        self.assertEqual(is_match({"age": None, "dob": None}, min_age=20), "Needs review")
        self.assertIsNone(parse_profile("hello everyone how are you"))
    def test_age(self):
        self.assertEqual(get_age("2000-12-02", today=date(2026, 10, 28)), 25)
        self.assertEqual(normalized_star("స్వాతి"), "swati")

if __name__ == "__main__":
    unittest.main()
