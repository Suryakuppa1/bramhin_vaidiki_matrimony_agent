import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import core
from core import parse_profile, store_profile, load_profiles, import_export_json, connect
from preferences import (read_filters, save_filters, configured, matching_rows,
                         describe_filters, empty_matches_reason)

PROFILE = '''Bride Profile
Name: Ananya
DOB: 14-07-1999
Nakshatram: Rohini
Place of Birth: Hyderabad
Education: B.Tech'''

class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = core.DB_PATH
        core.DB_PATH = Path(self.tmp.name) / 'profiles.sqlite3'
    def tearDown(self):
        core.DB_PATH = self.old
        self.tmp.cleanup()
    def test_save_and_match(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='consented matrimonial group', source_ref='1', source_kind='opt_in_bot', submitted_by='35')
        prefs = read_filters('123')
        self.assertFalse(configured(prefs))
        prefs.update(min_age=25, max_age=30, stars='రోహిణి', birthplace='Hyderabad')
        save_filters('123', prefs)
        self.assertEqual(len(matching_rows(load_profiles(), read_filters('123'))), 1)
        prefs['group'] = 'different group'
        self.assertEqual(matching_rows(load_profiles(), prefs), [])
        prefs['group'] = ''
        self.assertIn('Hyderabad', describe_filters(read_filters('123')))
        prefs['stars'] = 'Swathi'
        self.assertEqual(len(matching_rows(load_profiles(), prefs)), 0)
    def test_review_missing(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='group', source_ref='2', source_kind='opt_in_bot')
        f = dict(min_age=20, max_age=30, stars='Rohini', birthplace='', rashi='Vrishabha', education='', dob_start=None, dob_end=None)
        self.assertEqual(len(matching_rows(load_profiles(), f)), 0)
        self.assertEqual(matching_rows(load_profiles(), f, include_review=True)[0]['status'], 'Needs review')
    def test_underage_excluded(self):
        p = dict(name='Test', dob='2010-01-01', age=16, nakshatram='rohini')
        store_profile(p, source_name='group', source_ref='3', source_kind='opt_in_bot')
        f = dict(min_age=None, max_age=None, stars='Rohini', birthplace='', rashi='', education='', dob_start=None, dob_end=None, group='')
        self.assertEqual(matching_rows(load_profiles(), f), [])
    def test_empty_matches_reason_empty_db(self):
        f = dict(min_age=23, max_age=28, stars='', birthplace='', rashi='', education='', dob_start=None, dob_end=None, group='')
        msg = empty_matches_reason([], f)
        self.assertIn('database is empty', msg)
        self.assertIn('does not scrape', msg)
    def test_empty_matches_reason_needs_review(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='group', source_ref='4', source_kind='opt_in_bot')
        f = dict(min_age=20, max_age=30, stars='Rohini', birthplace='', rashi='Vrishabha', education='', dob_start=None, dob_end=None, group='')
        msg = empty_matches_reason(load_profiles(), f)
        self.assertIn('Needs review', msg)
        self.assertIn('/review', msg)
    def test_empty_matches_reason_group_filter(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='consented matrimonial group', source_ref='5', source_kind='opt_in_bot')
        f = dict(min_age=20, max_age=30, stars='Rohini', birthplace='', rashi='', education='', dob_start=None, dob_end=None, group='different group')
        msg = empty_matches_reason(load_profiles(), f)
        self.assertIn('/setgroup', msg)
    def test_reimport_keeps_one_canonical_match(self):
        """Re-importing the original message must not hide every copy from /matches."""
        p = parse_profile(PROFILE)
        store_profile(p, source_name='Group', source_ref='101', source_kind='telegram_export')
        store_profile(p, source_name='Group', source_ref='202', source_kind='telegram_export')
        store_profile(p, source_name='Group', source_ref='101', source_kind='telegram_export')
        rows = load_profiles()
        canonical = [r for r in rows if not r.get('duplicate_of')]
        duplicates = [r for r in rows if r.get('duplicate_of')]
        self.assertEqual(len(canonical), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(canonical[0]['source_ref'], '101')
        self.assertEqual(duplicates[0]['source_ref'], '202')
        self.assertEqual(duplicates[0]['duplicate_of'], canonical[0]['id'])
        f = dict(min_age=20, max_age=30, stars='Rohini', birthplace='', rashi='', education='', dob_start=None, dob_end=None, group='')
        self.assertEqual(len(matching_rows(rows, f)), 1)
    def test_load_repairs_mutual_duplicate_flags(self):
        p = parse_profile(PROFILE)
        store_profile(p, source_name='Group', source_ref='101', source_kind='telegram_export')
        store_profile(p, source_name='Group', source_ref='202', source_kind='telegram_export')
        rows = load_profiles()
        a, b = rows[0]['id'], rows[1]['id']
        con = connect()
        try:
            # Simulate the pre-fix bug: both rows point at each other.
            con.execute('UPDATE profiles SET duplicate_of=? WHERE id=?', (b, a))
            con.execute('UPDATE profiles SET duplicate_of=? WHERE id=?', (a, b))
            con.commit()
        finally:
            con.close()
        repaired = load_profiles()
        self.assertEqual(sum(1 for r in repaired if not r.get('duplicate_of')), 1)
        f = dict(min_age=20, max_age=30, stars='Rohini', birthplace='', rashi='', education='', dob_start=None, dob_end=None, group='')
        self.assertEqual(len(matching_rows(repaired, f)), 1)
if __name__ == '__main__':
    unittest.main()

class HistoryConsentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = core.DB_PATH
        core.DB_PATH = Path(self.tmp.name) / 'profiles.sqlite3'
    def tearDown(self):
        core.DB_PATH = self.old
        self.tmp.cleanup()
    def test_history_requires_explicit_consent_marker(self):
        import json
        payload = json.dumps({"name": "Sample", "messages": [
            {"type": "message", "id": 1, "text": PROFILE},
            {"type": "message", "id": 2, "text": "CONSENT:YES\n" + PROFILE},
        ]}).encode()
        accepted, skipped = import_export_json(payload, filename='sample.json', permission_confirmed=True)
        self.assertEqual(accepted, 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(load_profiles()), 1)
