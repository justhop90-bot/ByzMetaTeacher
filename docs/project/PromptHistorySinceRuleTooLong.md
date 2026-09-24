# Prompt History: Post-Lint Repair Phase

This file records the substantive prompts used after the rule-length repair phase so the teaching bot's repository retains the reasoning trail that produced the current audit.

1. "Check this and fix the errors before we continue. Deep dive into aoe2de community and learn the common coding mistakes. https://github.com/justhop90-bot/ByzMetaTeacher/blob/main/docs/audits/LintTeachReport.txt"

Purpose: audit the lint report against current AoE2DE community practice, distinguish real parser/rule-length failures from stale diagnostics, remove source artifacts such as Markdown fences, and preserve the teaching architecture.

2. "Trace the repeated raw threat conditions and fix them."

Purpose: centralize repeated enemy threat observations into state goals and replace duplicated raw predicates in strategy, production capacity, and military production consumers without changing their intended policy thresholds.

3. "Trace every threat-state goal from its writer to each consumer and flag any goal with no live downstream use."

Purpose: verify every threat-state goal has a live writer and downstream consumer, identify dead or functionally disconnected state, and distinguish positive consumers from negative safe-state gates.

4. "Audit the production rules that now consume threat-state goals and identify any behavior changes caused by replacing the original raw predicates."

Purpose: compare the state-goal consumers against the pre-replacement raw predicates and identify threshold drift, lost strategic branches, state-lifetime errors, and accidental merging of production-capacity thresholds with military-counter thresholds.

5. "Act professionally. Add the prompts we've discussed since the rule to long updates and update the git. Audit your update before you publish it."

Purpose: preserve this post-lint prompt trail and require a pre-publication structural audit of the source update.

## Resulting repair doctrine

Threat observations are state writers. Production-capacity thresholds and military-counter thresholds are separate policies and must not share a level goal merely because they observe the same unit family. Transient threat-state goals are reset before observation and then repopulated. Refactors must preserve the original consumer threshold unless an intentional gameplay change is explicitly requested. A structural audit is required before repository publication; it checks parenthesis balance, rule count, maximum direct rule children, source-line length, and presence of the intended dedicated counter goals.

6. "Deep dive and turn yourself into a aoe2de ai-script debugger expert. Then I give you full authority and autonomy. Trace this code line for line, front and back. Lock down the basics."

Purpose: perform a source-level debugger audit against current AoE2DE/AIRef command semantics and community practice, trace the controller from loader through initialization, state, strategy, production, training, attack, retreat, and research, then repair fatal parser/state-invariant defects before further gameplay work. The repair closed the malformed Pikeman rule, replaced invalid goal-negation syntax with documented NOT/goal form, and explicitly initialized all transient counter goals. The post-write structural audit verified 95 rules, 95 arrows, balanced parentheses, no nested top-level defrules, no logical-operator arity failures, no source line over 255 characters, and no remaining goal != predicates.

## Debugger doctrine

The debugger treats the .per source as an executable state machine, not as prose. Every symbol is traced from definition to writer to consumer; every writer is checked for initialization and lifetime; every consumer is checked for the correct comparison type; every action is checked for a corresponding world-state witness; and every claimed engine behavior is separated from community convention and architecture-specific inference. Structural cleanliness is necessary but never treated as runtime proof. The game remains the final debugger.
