from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

def extract_rule(text, start):
    depth = 0
    seen = False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
            seen = True
        elif ch == ")":
            depth -= 1
            if seen and depth == 0:
                return text[start:i + 1], i + 1
    raise SystemExit("unterminated defrule")

needle = "(defrule\n    (current-age >= imperial-age)\n    (goal byzantine-late-resource-burn 1)"
start = s.find(needle)
if start < 0:
    raise SystemExit("imperial farm rule anchor not found")

pos = start
while True:
    rule, end = extract_rule(s, pos)
    if "(goal demand-economy-farm-boom-imperial 0)" in rule and "(wood-amount > 5000)" in rule and "(or\n" in rule:
        break
    pos = s.find(needle, end)
    if pos < 0:
        raise SystemExit("target imperial farm rule not found")

actions = """=> 
    (set-goal demand-economy-farm-boom-imperial 1)
    (set-goal byzantine-surplus-spend-claim 1)
    (set-goal byzantine-surplus-spend-resource byzantine-surplus-resource-wood)
)"""

common = """    (current-age >= imperial-age)
    (goal byzantine-late-resource-burn 1)
    (goal byzantine-late-upgrade-priority 0)
    (goal byzantine-army-reinforcement 0)
    (goal byzantine-remote-resource-state byzantine-remote-resource-idle)
    (goal byzantine-market-state byzantine-market-idle)
    (goal demand-castle-cataphract-floor 0)
    (goal demand-castle-varangian-guard-floor 0)
    (goal demand-imperial-arbalester-floor 0)
    (goal demand-imperial-halberdier-floor 0)
    (goal demand-imperial-siege-ram-floor 0)
    (goal demand-imperial-trebuchet-floor 0)
    (goal demand-imperial-bombard-floor 0)
    (goal demand-economy-farm-boom-imperial 0)
    (goal demand-economy-house-floor-16 0)
    (goal byzantine-surplus-spend-claim 0)
    (wood-amount > 5000)
"""

new = """; Imperial farm boom is split by TC count so each native rule stays comfortably
; under DE's 32-element rule budget while preserving the same arbitration guards.
(defrule
""" + common + """    (not (building-type-count-total town-center >= 2))
    (building-type-count farm < bt-imperial-farm-target-1tc)
""" + actions + """

(defrule
""" + common + """    (building-type-count-total town-center >= 2)
    (not (building-type-count-total town-center >= 3))
    (building-type-count farm < bt-imperial-farm-target-2tc)
""" + actions + """

(defrule
""" + common + """    (building-type-count-total town-center >= 3)
    (building-type-count farm < bt-imperial-farm-target-3tc)
""" + actions

s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")
