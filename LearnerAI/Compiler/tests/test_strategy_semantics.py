import unittest
from dataclasses import replace

from LearnerAI.Compiler.ir.civ_profile import resolve_effective_civ
from LearnerAI.Compiler.clients.basilisk import (
    ByzantineProfile,
    ExecutionDemandTemplate,
    StrategyPosture,
    StrategicEvidenceKind,
    StrategicTargetKind,
    StrategicMilitaryComposition,
    build_byzantine_castle_strategy,
    build_byzantine_strategy,
    build_land_castle_strategy,
    lower_strategy_profile,
    resolve_strategy_profile,
)


class StrategySemanticsTests(unittest.TestCase):
    def setUp(self):