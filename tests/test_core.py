import unittest
from datetime import date
from core import parse_profile, is_match, get_age, normalized_star, canonical, SAKA_ALIASES, GOTRAM_ALIASES

SAMPLE = """Bride Profile
Name: Ananya
DOB: 14-07-1999
Nakshatram: Rohini
Rashi: Vrishabha
Gotram: Bharadwaja
Saka: Vaidiki Velanadu
Place of Birth: Vijayawada
Education: B.Tech
"""

TELUGU = """Bride Profile
CONSENT:YES
పేరు: శ్రీలేఖ
పుట్టిన తేదీ: 23/02/2002
నక్షత్రం: స్వాతి
రాశి: తుల
గోత్రం: కశ్యప
శాఖ: వైదికి వేలనాడు
జన్మస్థలం: హైదరాబాద్
విద్య: MBA
"""

class CoreTests(unittest.TestCase):
    def test_extraction(self):
        p = parse_profile(SAMPLE)
        self.assertEqual(p["name"], "Ananya")
        self.assertEqual(p["dob"], "1999-07-14")
        self.assertEqual(p["nakshatram"], "rohini")
        self.assertEqual(p["rashi"], "vrishabha")
        self.assertEqual(p["gotram"], "bharadwaja")
        self.assertEqual(p["saka"], "vaidiki_velanadu")
        self.assertEqual(p["birthplace"], "vijayawada")

    def test_telugu_extraction(self):
        p = parse_profile(TELUGU)
        self.assertEqual(p["nakshatram"], "swati")
        self.assertEqual(p["rashi"], "tula")
        self.assertEqual(p["gotram"], "kashyapa")
        self.assertEqual(p["saka"], "vaidiki_velanadu")
        self.assertEqual(p["birthplace"], "hyderabad")

    def test_match(self):
        p = parse_profile(SAMPLE)
        self.assertEqual(is_match(p, min_age=25, max_age=29, stars="రోహిణి", birthplace="Vijayawada"), "Match")
        self.assertEqual(is_match(p, stars="Swathi"), "No match")

    def test_bilingual_filters(self):
        english = parse_profile(SAMPLE)
        telugu = parse_profile(TELUGU)
        # English profile searched with Telugu filters
        self.assertEqual(is_match(english, stars="రోహిణి", rashi="వృషభ", gotram="భరద్వాజ",
                                  saka="వైదికి వేలనాడు"), "Match")
        # Telugu profile searched with English filters
        self.assertEqual(is_match(telugu, stars="Swathi", rashi="Tula", gotram="Kashyapa",
                                  saka="Vaidiki Velanadu", birthplace="Hyderabad"), "Match")
        self.assertEqual(is_match(english, saka="Niyogi"), "No match")
        self.assertEqual(is_match(english, name="Anan"), "Match")
        self.assertEqual(is_match(english, name="Priya"), "No match")

    def test_missing(self):
        self.assertEqual(is_match({"age": None, "dob": None}, min_age=20), "Needs review")
        self.assertIsNone(parse_profile("hello everyone how are you"))

    def test_age(self):
        self.assertEqual(get_age("2000-12-02", today=date(2026, 10, 28)), 25)
        self.assertEqual(normalized_star("స్వాతి"), "swati")
        self.assertEqual(canonical("వైదికి వేలనాడు", SAKA_ALIASES), "vaidiki_velanadu")
        self.assertEqual(canonical("Bharadwaj", GOTRAM_ALIASES), "bharadwaja")

    def test_mrigasira_spellings(self):
        for spelling in (
            "mrigasira", "Mrigashira", "Mriga Sira", "mrigasira nakshatram",
            "mrugasira", "మృగశిర", "మృగశీర్షం",
        ):
            self.assertEqual(normalized_star(spelling), "mrigashira", spelling)
        profile = {
            "name": "Test", "dob": "1999-07-14", "age": 27,
            "nakshatram": "Mriga Sira nakshatram", "rashi": None, "gotram": None,
            "saka": None, "birthplace": None, "education": None,
        }
        self.assertEqual(is_match(profile, stars="mrigasira"), "Match")
        self.assertEqual(is_match(profile, stars="మృగశీర్షం"), "Match")

if __name__ == "__main__":
    unittest.main()
