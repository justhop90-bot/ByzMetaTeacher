import unittest

from Compiler.oracles.duc_native import (
    DucOracleConsistencyError,
    validate_oracle_consistency,
)


class DucOracleConsistencyTests(unittest.TestCase):
    def _document(self):
        return {
            "fixture": {
                "id": "DUC-ORACLE-TEST",
                "assertions": [
                    {
                        "id": "probe",
                        "description": "Probe result exists.",
                        "observation_path": "/fixture/observation/probe/commands",
                    }
                ],
                "observation": {
                    "engine": {"build": "test"},
                    "result": "UNVERIFIED",
                    "list": {
                        "before": {"ids": [1, 2, 3]},
                        "after": {"ids": [1, 3]},
                    },
                    "target": {
                        "before": {
                            "selected": False,
                            "access_result": "NOT_ATTEMPTED",
                        },
                        "after": {
                            "selected": False,
                            "access_result": "NOT_ATTEMPTED",
                        },
                    },
                    "cursor": {
                        "before": None,
                        "after": None,
                        "transition": "UNOBSERVABLE",
                    },
                    "search_state": {
                        "before": {
                            "local_total": 3,
                            "local_last_search": 3,
                            "remote_total": 0,
                            "remote_last_search": 0,
                        },
                        "after": {
                            "local_total": 2,
                            "local_last_search": 0,
                            "remote_total": 0,
                            "remote_last_search": 0,
                        },
                    },
                    "probe": {
                        "commands": [
                            {"source": "(test)", "result": "SUCCESS"}
                        ]
                    },
                    "assertions": [
                        {"id": "probe", "result": "UNVERIFIED"}
                    ],
                },
            }
        }

    def test_unique_assertions_are_accepted(self):
        validate_oracle_consistency(self._document())

    def test_duplicate_assertion_ids_are_rejected(self):
        document = self._document()
        document["fixture"]["assertions"].append(
            {
                "id": "probe",
                "description": "Duplicate.",
            }
        )
        with self.assertRaisesRegex(DucOracleConsistencyError, "duplicate ids"):
            validate_oracle_consistency(document)

    def test_missing_assertion_reference_is_rejected(self):
        document = self._document()
        document["fixture"]["assertions"][0][
            "observation_path"
        ] = "/fixture/observation/missing"
        with self.assertRaisesRegex(DucOracleConsistencyError, "missing"):
            validate_oracle_consistency(document)


if __name__ == "__main__":
    unittest.main()
