import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / 'docs' / 'reference' / 'runtime-witness.schema.json'
SCENARIOS = ROOT / 'docs' / 'runtime' / 'scenarios'


class RuntimeWitnessSchemaTests(unittest.TestCase):
    def _read(self, name: str):
        return json.loads((SCENARIOS / name).read_text(encoding='utf-8'))

    def test_schema_declares_evidence_and_runtime_claim_contract(self):
        schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertEqual(schema['properties']['record_type']['enum'], ['SCENARIO', 'WITNESS'])
        self.assertIn('artifact', schema['required'])
        self.assertIn('evidence_class', schema['properties']['checkpoint']['items']['required'])

    def test_scenarios_have_open_status_and_do_not_claim_runtime_results(self):
        for name in ('arena-mild-pressure-castle.json', 'resource-camp-placement.json', 'attack-release-and-siege.json'):
            record = self._read(name)
            self.assertEqual(record['record_type'], 'SCENARIO')
            self.assertEqual(record['status'], 'OPEN')
            self.assertIsNone(record['artifact']['sha256'])
            for claim in record['claims']:
                self.assertIn(claim['evidence_class'], {'ENGINE FACT', 'COMMUNITY PRACTICE', 'COMPILER POLICY', 'OPEN / UNKNOWN'})

    def test_arena_scenario_binds_known_repair_and_castle_witness_edges(self):
        record = self._read('arena-mild-pressure-castle.json')
        rule_ids = {rule for claim in record['claims'] for rule in claim['rule_identities']}
        self.assertIn('opening-selector-fast-castle', rule_ids)
        self.assertIn('economy-controller-select-counter-pressure', rule_ids)
        self.assertIn('civilian-villager-continuity', rule_ids)
        self.assertIn('castle-age-transition', rule_ids)
        edges = {claim['lifecycle_edge'] for claim in record['claims']}
        self.assertIn('ARBITRATION -> EXECUTION', edges)
        self.assertIn('ACTION -> WORLD-STATE WITNESS', edges)

    def test_runtime_scenario_ids_are_unique(self):
        ids = []
        for path in sorted(SCENARIOS.glob('*.json')):
            record = json.loads(path.read_text(encoding='utf-8'))
            ids.append(record['scenario_id'])
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main()
