import tempfile
import unittest
from pathlib import Path

import core
from core import parse_profile, store_profile, load_profiles, field_value_counts, STAR_ALIASES
from menu import build_field_options, display_value, home_keyboard, options_keyboard


PROFILE = '''Bride Profile
Name: Ananya
DOB: 14-07-1999
Nakshatram: Rohini
Rashi: Vrishabha
Gotram: Bharadwaja
Saka: Vaidiki Velanadu
Place of Birth: Hyderabad
Education: B.Tech'''


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = core.DB_PATH
        core.DB_PATH = Path(self.tmp.name) / 'profiles.sqlite3'

    def tearDown(self):
        core.DB_PATH = self.old
        self.tmp.cleanup()

    def test_field_value_counts_and_keyboard(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='Group A', source_ref='1', source_kind='opt_in_bot')
        stars = field_value_counts(load_profiles(), field='nakshatram', alias_map=STAR_ALIASES)
        self.assertEqual(stars[0][0], 'rohini')
        self.assertEqual(stars[0][1], 1)
        opts = build_field_options('stars')
        self.assertEqual(opts[0][0], 'rohini')
        kb = options_keyboard('stars', opts)
        self.assertTrue(any(btn.callback_data.startswith('menu:set:stars:') for row in kb.inline_keyboard for btn in row))
        home = home_keyboard()
        self.assertTrue(any(btn.callback_data == 'menu:list:stars' for row in home.inline_keyboard for btn in row))
        self.assertEqual(display_value('vaidiki_velanadu'), 'Vaidiki Velanadu')


if __name__ == '__main__':
    unittest.main()
