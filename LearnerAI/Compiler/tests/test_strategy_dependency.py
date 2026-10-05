import unittest
from types import SimpleNamespace

from Compiler.diagnostics import DiagnosticSeverity
from Compiler.ir.capability import (
    CapabilityGraph,
    CapabilityId,
    DemandId,
    ProviderId,
)
from Compiler.semantic.capability_validation import (
    CapabilityDiagnosticCode,
    GraphDiagnostic,
    ValidationReport,
)
from Compiler.semantic.rule_execution import RuleExecutionReport, RuleReachabilityReport
from Compiler.semantic.persistent_state import PersistentStateReport
from Compiler.semantic.strategy_dependency import (
    StrategyDependencyCode,
    StrategyDependencyProof,
    analyze_strategy_dependencies,
)
from Compiler.ir.native_duc import NativeDucLifecycleStage, NativeDucPlan, NativeDucRule


def _demand(name="d"):
    return SimpleNamespace(
        identity=DemandId("test", name),
        target=CapabilityId("test", f"{name}-cap"),
        location=None,
    )


def _provider(name="d"):
    return SimpleNamespace(
        identity=ProviderId("test", f"{name}-provider"),
        capability=CapabilityId("test", f"{name}-cap"),
        kind=SimpleNamespace(value="CONSTRUCTION"),
        prerequisites=(),
        witness=None,
        action=SimpleNamespace(
            primitive="build",
            arguments=("lumber-camp",),
        ),
        location=None,
    )


class StrategyDependencyTests(unittest.TestCase):
    def _graph(self, demand, providers=()):
        return CapabilityGraph(
            demands=(demand,),
            capabilities=(SimpleNamespace(identity=demand.target, location=None),),
            providers=tuple(providers),
            witnesses=(),
            edges=(),
        )

    def _empty_state(self):
        return PersistentStateReport((), (), ())

    def test_providerless_demand_is_proven_error(self):
        demand = _demand()
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand),
            ValidationReport((
                GraphDiagnostic(
                    CapabilityDiagnosticCode.PROVIDERLESS_CAPABILITY,
                    DiagnosticSeverity.ERROR,
                    "no provider",
                    node=demand.identity,
                ),
            )),
            RuleExecutionReport((), (), RuleReachabilityReport((), (), (), ())),
            self._empty_state(),
        )
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].code, StrategyDependencyCode.PROVIDERLESS_DEMAND)
        self.assertEqual(report.errors[0].proof, StrategyDependencyProof.PROVEN)

    def test_action_without_emitted_rule_is_execution_blocker(self):
        demand = _demand()
        provider = _provider()
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand, (provider,)),
            ValidationReport(()),
            RuleExecutionReport((), (), RuleReachabilityReport((), (), (), ())),
            self._empty_state(),
        )
        self.assertEqual(
            report.errors[0].code,
            StrategyDependencyCode.EXECUTION_UNREACHABLE,
        )
        self.assertIn("no emitted rule", report.errors[0].message)

    def test_unrooted_capability_cycle_is_correlated_to_demand(self):
        demand = _demand()
        provider = _provider()
        diag = GraphDiagnostic(
            CapabilityDiagnosticCode.CYCLE,
            DiagnosticSeverity.ERROR,
            "unrooted capability dependency cycle",
            node=provider.identity,
            related=(demand.target,),
        )
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand, (provider,)),
            ValidationReport((diag,)),
            RuleExecutionReport(
                (
                    SimpleNamespace(
                        rule_order=7,
                        actions=(
                            SimpleNamespace(
                                expression=SimpleNamespace(
                                    head="build",
                                    args=("lumber-camp",),
                                ),
                            ),
                        ),
                    ),
                ),
                (),
                RuleReachabilityReport((7,), (), (), ()),
            ),
            self._empty_state(),
        )
        finding = next(
            item for item in report.findings
            if item.code is StrategyDependencyCode.UNROOTED_CYCLE
        )
        self.assertEqual(finding.proof, StrategyDependencyProof.PROVEN)
        self.assertEqual(finding.root_demand, "DemandId:test:d")

    def test_missing_persistent_writer_is_correlated(self):
        demand = _demand()
        boundary = SimpleNamespace(
            state=SimpleNamespace(
                kind=SimpleNamespace(value="GOAL"),
                identifier="strategy-test",
            ),
            readers=(
                SimpleNamespace(rule_order=12, location=None),
            ),
            first_writer=None,
        )
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand),
            ValidationReport(()),
            RuleExecutionReport((), (), RuleReachabilityReport((), (), (), ())),
            PersistentStateReport((), (boundary,), ()),
        )
        finding = next(
            item for item in report.findings
            if item.code is StrategyDependencyCode.MISSING_STATE_PRODUCER
        )
        self.assertEqual(finding.proof, StrategyDependencyProof.PROVEN)
        self.assertEqual(finding.rule_orders, (12,))

    def test_compiler_owned_relic_lifecycle_is_reported_deterministically(self):
        demand = _demand()
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="byzantine-relic-control-acquire",
                    order=0,
                    facts=(SimpleNamespace(source="(true)"),),
                    actions=(),
                    lifecycle=(
                        NativeDucLifecycleStage.ADMISSIBILITY,
                        NativeDucLifecycleStage.TARGET,
                        NativeDucLifecycleStage.DISPATCH,
                    ),
                ),
                NativeDucRule(
                    identity="byzantine-relic-control-pickup-witness",
                    order=1,
                    facts=(SimpleNamespace(source="(true)"),),
                    actions=(),
                    lifecycle=(NativeDucLifecycleStage.PICKUP_WITNESS,),
                ),
                NativeDucRule(
                    identity="byzantine-relic-control-return",
                    order=2,
                    facts=(SimpleNamespace(source="(true)"),),
                    actions=(),
                    lifecycle=(NativeDucLifecycleStage.RETURN,),
                ),
                NativeDucRule(
                    identity="byzantine-relic-control-release-witness",
                    order=3,
                    facts=(SimpleNamespace(source="(true)"),),
                    actions=(),
                    lifecycle=(NativeDucLifecycleStage.RELEASE_WITNESS,),
                ),
                NativeDucRule(
                    identity="byzantine-relic-control-recovery",
                    order=4,
                    facts=(SimpleNamespace(source="(true)"),),
                    actions=(),
                    lifecycle=(NativeDucLifecycleStage.RECOVERY,),
                ),
            ),
        )
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand),
            ValidationReport(()),
            RuleExecutionReport((), (), RuleReachabilityReport((), (), (), ())),
            self._empty_state(),
            duc_plan=plan,
        )
        codes = tuple(item.code for item in report.findings)
        self.assertIn(
            StrategyDependencyCode.RELIC_LIFECYCLE_CONNECTED,
            codes,
        )
        self.assertIn(
            StrategyDependencyCode.RELIC_RELEASE_WITNESS_OPEN,
            codes,
        )
        self.assertEqual(report.to_json(), report.to_json())

    def test_json_is_deterministic(self):
        demand = _demand()
        report = analyze_strategy_dependencies(
            (demand,),
            self._graph(demand),
            ValidationReport(()),
            RuleExecutionReport((), (), RuleReachabilityReport((), (), (), ())),
            self._empty_state(),
        )
        self.assertEqual(report.to_json(), report.to_json())
        self.assertIn('"schema_version": 1', report.to_json())


if __name__ == "__main__":
    unittest.main()
