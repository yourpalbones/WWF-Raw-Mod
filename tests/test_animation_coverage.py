"""ROM-free checks for the coverage inventory and Perfect-Plex receiver recipes."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_animation_coverage as coverage  # noqa: E402
from check_perfect_receivers import analyse, profile_parts  # noqa: E402


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = coverage.build()

    def test_committed_outputs_are_current(self):
        committed = json.loads((ROOT / 'data/animation-coverage.json').read_text())
        self.assertEqual(committed, json.loads(json.dumps(self.data)))

    def test_all_thirteen_slots_present(self):
        self.assertEqual([s['slot'] for s in self.data['slots']], list(range(13)))

    def test_every_slot_has_perfect_plex_receiver_target(self):
        targets = {r['slot'] for r in self.data['rows']
                   if r['action'] == 'finisher:Perfect-Plex' and r['role'] == 'receiver'
                   and r.get('variant', '').startswith('target')}
        self.assertEqual(targets, set(range(13)))

    def test_visual_verification_requires_evidence(self):
        for r in self.data['rows']:
            if r['gameplay_status'] in ('verified_visual', 'verified_functional', 'defective'):
                self.assertTrue(r['evidence'], r)

    def test_no_completeness_claim(self):
        self.assertIn('NOT', self.data['claim'])
        self.assertFalse(any(r['art_status'] == 'missing' and r['gameplay_status'] != 'untested'
                             for r in self.data['rows']))


class ReceiverTests(unittest.TestCase):
    def test_profile_parser(self):
        parts = profile_parts(bytes([0x10, 0x0e, 32, 0, 0x24, 0x80, 0, 0xff, 0xff, 0xff]))
        self.assertEqual(parts, [{'id': 0xe10, 'dx': 32, 'dy': 0}, {'id': 0x8024, 'dx': 0, 'dy': -1}])

    def test_receiver_recipes(self):
        result = analyse(json.loads((ROOT / 'data/perfect-receivers.json').read_text()))
        status = {f['id']: f['severity'] for f in result['findings']}
        self.assertEqual([status[k] for k in ('S1', 'S2', 'S3')], ['pass'] * 3)
        # S4 is a historical fact about copied bytes, not a regression check on a build.
        self.assertEqual(status['S4'], 'info')


class PairCoordinateTests(unittest.TestCase):
    def test_outputs_current_and_cases_complete(self):
        import derive_perfect_pair_coordinates as pair
        observed, source = pair.observed_positions()
        data = pair.report(observed, source)
        committed = json.loads((ROOT / 'evidence/perfect-plex-receivers/pair-coordinates.json').read_text())
        self.assertEqual(committed, json.loads(json.dumps(data)))
        self.assertEqual(len(data['cases']), 12)
        self.assertIn('PREDICTION', data['status'])

    def test_reflection_rules(self):
        import derive_perfect_pair_coordinates as pair
        self.assertEqual(pair.screen(100, 5, 0, True, 'edge', True), 94)
        self.assertEqual(pair.screen(100, 5, 0, True, 'centre', True), 95)
        self.assertEqual(pair.screen(100, 5, 32, True, 'edge', True), 62)
        self.assertEqual(pair.screen(100, 5, 32, False, 'edge', True), 137)
        self.assertEqual(pair.screen(100, 5, 0, True, 'native+8', True), 102)


if __name__ == '__main__':
    unittest.main()
